from flask import Blueprint, jsonify, request
from firebase_admin import firestore
import datetime
from service.notification import create_admin_notification
from exponent_server_sdk import PushClient, PushMessage, PushServerError

notification_bp = Blueprint('notification', __name__)

def get_db():
    """Lazy initialization of Firestore client"""
    return firestore.client()


@notification_bp.route('/save-push-token', methods=['POST'])
def save_push_token():
    try:
        db = get_db()
        data = request.get_json(silent=True) or {}
        uid = data.get('uid')
        token = data.get('token')

        if not uid or not token:
            return jsonify({"status": False, "error": "Missing uid or token"}), 400

        # Store both key styles for backward compatibility
        db.collection('users').document(uid).set({
            'push_token': token,
            'pushToken': token,
            'push_token_updated_at': datetime.datetime.now()
        }, merge=True)

        return jsonify({"status": True, "message": "Push token saved"}), 200
    except Exception as e:
        print(f"Save push token error: {str(e)}")
        return jsonify({"status": False, "error": str(e)}), 500


@notification_bp.route('/send-notification', methods=['POST'])
def send_notification():
    try:
        db = get_db()
        data = request.get_json(silent=True) or {}
        uid = data.get('uid')
        title = data.get('title', 'Notification')
        body = data.get('body', '')
        payload_data = data.get('data', {})

        if not uid:
            return jsonify({"status": False, "error": "Missing uid"}), 400

        user_doc = db.collection('users').document(uid).get()
        if not user_doc.exists:
            return jsonify({"status": False, "error": "User not found"}), 404

        user_data = user_doc.to_dict() or {}
        token = user_data.get('push_token') or user_data.get('pushToken')
        if not token:
            return jsonify({"status": False, "error": "No push token for user"}), 400

        response = PushClient().publish(
            PushMessage(
                to=token,
                title=title,
                body=body,
                data=payload_data
            )
        )

        # Optional: log to admin notifications feed
        create_admin_notification(
            title=title,
            message=body,
            type="push_sent",
            metadata={"user_id": uid, "token": token[:20] + '...'}
        )

        return jsonify({"status": True, "message": "Notification sent", "provider": str(response)}), 200
    except PushServerError as e:
        print(f"Push server error: {str(e)}")
        return jsonify({"status": False, "error": "Push provider error"}), 502
    except Exception as e:
        print(f"Send notification error: {str(e)}")
        return jsonify({"status": False, "error": str(e)}), 500

@notification_bp.route('/admin/notifications', methods=['GET'])
def get_notifications():
    try:
        db = get_db()
        notifications_ref = db.collection('admin_notifications').order_by('created_at', direction=firestore.Query.DESCENDING).limit(50)
        notifications = []

        for doc in notifications_ref.stream():
            notification = doc.to_dict()
            notification['id'] = doc.id
            notifications.append(notification)

        return jsonify(notifications)
    except Exception as e:
        print(f"Get notifications error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@notification_bp.route('/admin/notifications/<notification_id>/read', methods=['PUT'])
def mark_notification_read(notification_id):
    try:
        db = get_db()
        db.collection('admin_notifications').document(notification_id).update({
            'read': True,
            'read_at': datetime.datetime.now()
        })
        return jsonify({"success": True})
    except Exception as e:
        print(f"Mark notification read error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@notification_bp.route('/admin/notifications/mark-all-read', methods=['PUT'])
def mark_all_notifications_read():
    try:
        db = get_db()
        batch = db.batch()
        notifications_ref = db.collection('admin_notifications').where('read', '==', False)

        for doc in notifications_ref.stream():
            batch.update(doc.reference, {
                'read': True,
                'read_at': datetime.datetime.now()
            })

        batch.commit()
        return jsonify({"success": True})
    except Exception as e:
        print(f"Mark all notifications read error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@notification_bp.route('/admin/users/<user_id>', methods=['PUT'])
def update_user_profile(user_id):
    try:
        db = get_db()
        data = request.get_json()

        # Update user document
        user_updates = {}
        if 'displayName' in data:
            user_updates['displayName'] = data['displayName']
        if 'email' in data:
            user_updates['email'] = data['email']
        if 'phone' in data:
            user_updates['phone'] = data['phone']
        if 'isActive' in data:
            user_updates['isActive'] = data['isActive']

        if user_updates:
            db.collection('users').document(user_id).update(user_updates)

        # Create notification for profile update
        create_admin_notification(
            title="User Profile Updated",
            message=f"Profile updated for user {user_id}",
            type="user_update",
            metadata={"user_id": user_id, "updates": user_updates}
        )

        return jsonify({"success": True})
    except Exception as e:
        print(f"Update user profile error: {str(e)}")
        return jsonify({"error": str(e)}), 500