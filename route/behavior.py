import datetime
import os
import hashlib
import logging
from flask import Blueprint, request, jsonify, g
from firebase_admin import firestore, auth
from middleware.auth import verify_firebase_token
import config.firebaseconfig
from service.send_email import send_eden_email
from service.email_template import get_waitlist_template

logger = logging.getLogger(__name__)

behavior_bp = Blueprint("behavior", __name__)
db = firestore.client()

def get_auth_user_id():
    """Helper to extract user ID from bearer token if present, without failing if missing."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    try:
        parts = auth_header.split(" ")
        if len(parts) < 2:
            return None
        token = parts[1]
        decoded_token = auth.verify_id_token(token)
        return decoded_token.get("uid")
    except Exception:
        return None

@behavior_bp.route('/behavior/track', methods=['POST'])
def track_behavior():
    try:
        data = request.json or {}
        action = data.get('action')
        path = data.get('path')
        metadata = data.get('metadata', {})
        platform = data.get('platform', 'web')
        anonymous_id = data.get('anonymousId')
        
        if not action:
            return jsonify({"status": False, "message": "Missing action"}), 400
            
        user_id = get_auth_user_id()
        
        db.collection('behavior_logs').add({
            "userId": user_id,
            "anonymousId": anonymous_id,
            "action": action,
            "path": path,
            "metadata": metadata,
            "platform": platform,
            "userAgent": request.headers.get('User-Agent'),
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        return jsonify({"status": True, "message": "Event tracked"}), 201
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500

@behavior_bp.route('/waitlist/join', methods=['POST'])
def join_waitlist():
    """Join waitlist.

    This endpoint supports two modes:
    - Authenticated: when a valid Firebase token is provided, dynamically resolved via token lookup.
    - Public testing: when env `ALLOW_PUBLIC_WAITLIST` is true, accepts unauthenticated joins using the posted email.
    """
    try:
        data = request.json or {}
        platform = data.get('platform', 'web')
        
        # Extract user identity safely without requiring explicit decorator enforcement
        uid = get_auth_user_id()
        email = None
        user_name = None

        if uid:
            try:
                # Fetch fresh profile record from Firebase instance since middleware is bypassed
                user_record = auth.get_user(uid)
                email = user_record.email
                # Try getting display name if available in custom user details
                user_name = getattr(user_record, 'display_name', None)
            except Exception as auth_err:
                logger.warning(f"Failed to fetch Firebase profile details for uid {uid}: {auth_err}")

        # Extract payload inputs and process environmental overrides
        email = data.get('email', email)
        allow_public = os.getenv('ALLOW_PUBLIC_WAITLIST', 'false').strip().lower() in ('1', 'true', 'yes')

        if not uid and not allow_public:
            return jsonify({"status": False, "message": "Authentication required"}), 401

        if not email:
            return jsonify({"status": False, "message": "Email is required"}), 400

        # Generate fallback structural layout if processing public traffic logs
        if not uid:
            digest = hashlib.md5(email.encode('utf-8')).hexdigest()
            uid = f"public:{digest}"

        # Persist entry directly using deterministic keys to enforce structural uniqueness
        db.collection('waitlist').document(uid).set({
            "userId": uid,
            "email": email,
            "platform": platform,
            "createdAt": firestore.SERVER_TIMESTAMP
        })

        # Record event logs tracking waitlist conversion details
        db.collection('behavior_logs').add({
            "userId": uid,
            "anonymousId": None,
            "action": "join_waitlist",
            "path": "/",
            "metadata": {"email": email},
            "platform": platform,
            "userAgent": request.headers.get('User-Agent'),
            "createdAt": firestore.SERVER_TIMESTAMP
        })

        # Fire asynchronous background mailing pipeline (best-effort execution context)
        try:
            subject = "You're on The New Eden waitlist — thanks for joining!"
            body_html = get_waitlist_template(user_name=user_name, email=email)
            send_eden_email(subject, email, body_html, background=True)
        except Exception as email_err:
            logger.error(f"Non-blocking email failure inside waitlist loop: {email_err}")

        return jsonify({"status": True, "message": "Successfully joined waitlist"}), 200
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500

@behavior_bp.route('/ratings', methods=['POST'])
def submit_rating():
    try:
        data = request.json or {}
        rating = data.get('rating')
        feedback = data.get('feedback', '')
        order_id = data.get('orderId')
        platform = data.get('platform', 'web')
        
        if rating is None:
            return jsonify({"status": False, "message": "Rating is required"}), 400
            
        try:
            rating = int(rating)
        except ValueError:
            return jsonify({"status": False, "message": "Rating must be an integer"}), 400
            
        if rating < 1 or rating > 5:
            return jsonify({"status": False, "message": "Rating must be between 1 and 5"}), 400
            
        user_id = get_auth_user_id()
        
        db.collection('ratings').add({
            "userId": user_id,
            "orderId": order_id,
            "rating": rating,
            "feedback": feedback,
            "platform": platform,
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        # Track rating action activity
        db.collection('behavior_logs').add({
            "userId": user_id,
            "anonymousId": None,
            "action": "submit_rating",
            "path": "/checkout/success",
            "metadata": {"rating": rating, "orderId": order_id},
            "platform": platform,
            "userAgent": request.headers.get('User-Agent'),
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({"status": True, "message": "Rating submitted successfully"}), 201
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500

@behavior_bp.route('/admin/behavior-stats', methods=['GET'])
def get_behavior_stats():
    try:
        users_stream = db.collection('users').stream()
        user_map = {}
        for doc in users_stream:
            u = doc.to_dict()
            uid = u.get('uid')
            if uid:
                user_map[uid] = {
                    "email": u.get('email', ''),
                    "fullName": u.get('fullName', 'Unknown User')
                }

        # 1. Fetch Waitlist Subscribers
        waitlist_stream = db.collection('waitlist').order_by('createdAt', direction=firestore.Query.DESCENDING).stream()
        waitlist_list = []
        platform_waitlist = {}
        for doc in waitlist_stream:
            w = doc.to_dict()
            uid = w.get('userId')
            created_at = w.get('createdAt')
            created_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else 'Unknown'
            
            email = w.get('email', '')
            name = 'Registered User'
            if uid in user_map:
                email = user_map[uid].get('email', email)
                name = user_map[uid].get('fullName', name)
            elif uid and uid.startswith("public:"):
                name = "Public Tester"
                
            plat = w.get('platform', 'web')
            platform_waitlist[plat] = platform_waitlist.get(plat, 0) + 1
            
            waitlist_list.append({
                "userId": uid,
                "email": email,
                "name": name,
                "platform": plat,
                "createdAt": created_str
            })

        # 2. Fetch Experience Ratings
        ratings_stream = db.collection('ratings').order_by('createdAt', direction=firestore.Query.DESCENDING).stream()
        ratings_list = []
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_stars = 0
        
        for doc in ratings_stream:
            r = doc.to_dict()
            uid = r.get('userId')
            created_at = r.get('createdAt')
            created_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else 'Unknown'
            
            email = 'Guest User'
            name = 'Guest'
            if uid and uid in user_map:
                email = user_map[uid].get('email', email)
                name = user_map[uid].get('fullName', name)
                
            stars = r.get('rating', 5)
            rating_distribution[stars] = rating_distribution.get(stars, 0) + 1
            total_stars += stars
            
            ratings_list.append({
                "userId": uid,
                "email": email,
                "name": name,
                "orderId": r.get('orderId', 'N/A'),
                "rating": stars,
                "feedback": r.get('feedback', ''),
                "platform": r.get('platform', 'web'),
                "createdAt": created_str
            })
            
        avg_rating = total_stars / len(ratings_list) if ratings_list else 0.0

        # 3. Fetch Behavior Logs
        logs_stream = db.collection('behavior_logs').order_by('createdAt', direction=firestore.Query.DESCENDING).limit(100).stream()
        recent_logs = []
        page_views = {}
        action_counts = {}
        platform_actions = {}
        
        for doc in logs_stream:
            log = doc.to_dict()
            uid = log.get('userId')
            created_at = log.get('createdAt')
            created_str = created_at.strftime('%Y-%m-%d %H:%M:%S') if created_at else 'Unknown'
            
            email = 'Guest'
            name = 'Guest'
            if uid and uid in user_map:
                email = user_map[uid].get('email', email)
                name = user_map[uid].get('fullName', name)
            elif uid and uid.startswith("public:"):
                email = log.get('metadata', {}).get('email', 'Public Email')
                name = "Public Tester"
            elif log.get('anonymousId'):
                email = f"Guest ({log.get('anonymousId')[:8]})"
                
            action = log.get('action', 'unknown')
            path = log.get('path', '/')
            plat = log.get('platform', 'web')
            
            # Aggregate stats
            action_counts[action] = action_counts.get(action, 0) + 1
            platform_actions[plat] = platform_actions.get(plat, 0) + 1
            if action == 'page_view':
                page_views[path] = page_views.get(path, 0) + 1
                
            recent_logs.append({
                "userId": uid,
                "anonymousId": log.get('anonymousId'),
                "email": email,
                "name": name,
                "action": action,
                "path": path,
                "metadata": log.get('metadata', {}),
                "platform": plat,
                "createdAt": created_str
            })

        # Top performance aggregations
        sorted_pages = sorted(page_views.items(), key=lambda x: x[1], reverse=True)[:10]
        top_pages = [{"path": p, "views": v} for p, v in sorted_pages]
        formatted_actions = [{"action": a, "count": c} for a, c in action_counts.items()]

        return jsonify({
            "waitlist": {
                "total": len(waitlist_list),
                "list": waitlist_list,
                "platforms": platform_waitlist
            },
            "ratings": {
                "total": len(ratings_list),
                "average": round(avg_rating, 2),
                "distribution": rating_distribution,
                "list": ratings_list
            },
            "behavior": {
                "recentLogs": recent_logs,
                "topPages": top_pages,
                "actions": formatted_actions,
                "platforms": platform_actions
            }
        }), 200
    except Exception as e:
        return jsonify({"status": False, "error": str(e)}), 500