import datetime 

from flask import Blueprint, request, jsonify, g
from firebase_admin import firestore
from flask_mail import Message # 1. Import Message
from middleware.auth import verify_firebase_token
from service.email_template import get_welcome_template # 2. Import Template
from service.send_email import send_eden_email
import config.firebaseconfig

sync_user_bp = Blueprint("sync_user", __name__)
db = firestore.client()


@sync_user_bp.route('/save-push-token', methods=['POST'])
def save_token():
    try:
        data = request.json
        uid = data.get('uid')
        token = data.get('token')
        
        if not uid or not token:
            return jsonify({"status": False, "message": "Missing UID or Token"}), 400

        # USING SET WITH MERGE=TRUE
        # This says: "If the doc exists, only update the pushToken. 
        # If it doesn't exist, create it with just this field."
        db.collection('users').document(uid).set({
            "pushToken": token,
            "lastTokenUpdate": datetime.datetime.now() # Good for debugging!
        }, merge=True)

        return jsonify({"status": True, "message": "Token saved safely"}), 200
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500




@sync_user_bp.route("/sync-user", methods=["POST"])
@verify_firebase_token
def sync_user():
    uid = g.user["uid"]
    email = g.user.get("email")

    data = request.json or {}
    state = data.get("state")
    full_name = data.get("fullName")
    role = 'buyer'
    photoUrl = ''
    phoneNumber = ''

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if not user_doc.exists:
        user_ref.set({
            "uid": uid,
            "email": email,
            "fullName": full_name,
            "state": state,
            "role": role,
            "address": {
                "street": "",
                "city": "",
                "state": state or "Lagos",
                "country": "Nigeria"
            },
            "photoURL": photoUrl,
            "phoneNumber": phoneNumber,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP
        })

        # --- 4. Send Welcome Email ---
        try:
            # Generate the HTML using your helper
            html_content = get_welcome_template(full_name or "Valued Member")
            
            send_eden_email(
                subject="Welcome to The New Eden! 🌿",
                recipients=[email],
                html=html_content
            )

           

        except Exception as e:
            # We don't want to crash the whole signup if the email fails
            print(f"❌ Failed to send welcome email: {e}")

        return jsonify({"message": "User created"}), 201

    # either user existed already and it is a regular registered profile
    # or this is just a re-sync. We do not override role on regular signup.
    response = jsonify({"message": "User already exists"}), 200

    return response


@sync_user_bp.route('/sync-guest', methods=['POST'])
def sync_guest_user():
    data = request.json or {}
    uid = data.get('uid')

    if not uid:
        return jsonify({"error": "Guest UID required"}), 400

    email = data.get('email', '').strip()
    full_name = data.get('fullName', 'Guest User')
    state = data.get('state', 'Unknown')

    user_ref = db.collection('users').document(uid)
    user_doc = user_ref.get()

    user_payload = {
        'uid': uid,
        'email': email,
        'fullName': full_name,
        'state': state,
        'role': 'guest',
        'address': {
            'street': '',
            'city': '',
            'state': state,
            'country': 'Nigeria'
        },
        'photoURL': data.get('photoURL', ''),
        'phoneNumber': data.get('phoneNumber', ''),
        'createdAt': firestore.SERVER_TIMESTAMP,
        'updatedAt': firestore.SERVER_TIMESTAMP,
        'isGuest': True
    }

    if not user_doc.exists:
        user_ref.set(user_payload)

        if email and '@' in email:
            try:
                html_content = get_welcome_template(full_name or 'Guest User')
                send_eden_email(
                    subject='Welcome to The New Eden (Guest Mode) 🌿',
                    recipients=[email],
                    html=html_content
                )
            except Exception as e:
                print(f"❌ Failed to send guest welcome email: {e}")

        return jsonify({"message": "Guest user synced"}), 201

    user_ref.update({
        'updatedAt': firestore.SERVER_TIMESTAMP,
        'role': 'guest',
        'isGuest': True
    })

    return jsonify({"message": "Guest user already exists, updated"}), 200