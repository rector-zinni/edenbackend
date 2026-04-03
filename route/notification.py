from flask import Blueprint, jsonify, request
from firebase_admin import firestore
import datetime
from service.notification import create_admin_notification
import logging
import requests

notification_bp = Blueprint('notification', __name__)

def get_db():
    """Lazy initialization of Firestore client"""
    return firestore.client()

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
    


@notification_bp.route('/save-push-token', methods=['POST'])
def save_push_token():
    try:
        data = request.get_json(silent=True) or {}
        uid = data.get('uid')
        token = data.get('token')

        if not uid or not token:
            return jsonify({'error': 'Missing uid or token'}), 400

        # Upsert user document with push_token (safe even if doc doesn't exist yet)
        user_ref = get_db.collection('users').document(uid)
        user_ref.set({'push_token': token}, merge=True)

        logging.info(f'Saved push token for user {uid}')
        return jsonify({'status': True, 'message': 'Push token saved'}), 200
    except Exception as e:
        logging.error(f'Error saving push token: {e}')
        return jsonify({'status': False, 'error': 'Failed to save token'}), 500

@notification_bp.route('/send-notification', methods=['POST'])
def send_notification():
    try:
        data = request.get_json(silent=True) or {}
        uid = data.get('uid')
        title = data.get('title', 'Notification')
        body = data.get('body', '')
        data_payload = data.get('data', {})

        if not uid:
            return jsonify({'error': 'Missing uid'}), 400

        # Get user push token
        user_ref = get_db().collection('users').document(uid)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        token = user_doc.to_dict().get('push_token')
        if not token:
            return jsonify({'error': 'No push token for user'}), 400

        # Send via Expo push API
        expo_url = 'https://exp.host/--/api/v2/push/send'
        payload = {
            'to': token,
            'title': title,
            'body': body,
            'data': data_payload
        }
        response = requests.post(expo_url, json=payload, timeout=15)
        expo_result = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}

        if response.status_code == 200 and expo_result.get('data', {}).get('status') in ('ok', None):
            logging.info(f'Sent notification to user {uid}')
            return jsonify({'status': True, 'message': 'Notification sent', 'provider': expo_result}), 200
        else:
            logging.error(f'Failed to send notification: {response.text}')
            return jsonify({'status': False, 'error': 'Failed to send', 'provider': expo_result}), 500
    except Exception as e:
        logging.error(f'Error sending notification: {e}')
        return jsonify({'status': False, 'error': 'Failed to send notification'}), 500