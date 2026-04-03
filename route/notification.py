from flask import Blueprint, jsonify, request
from firebase_admin import firestore
import datetime
from service.notification import create_admin_notification

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