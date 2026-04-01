from exponent_server_sdk import PushClient, PushMessage
from firebase_admin import firestore
import datetime

def get_db():
    """Lazy initialization of Firestore client"""
    return firestore.client()

def send_push_notification(user_id, title, body):
    db = get_db()
    user_doc = db.collection('users').document(user_id).get()
    if user_doc.exists:
        token = user_doc.to_dict().get('pushToken')
        if token:
            try:
                response = PushClient().publish(
                    PushMessage(to=token, title=title, body=body, data={"type": "order_update"})
                )
                print(f"Push Sent: {response}")
            except Exception as e:
                print(f"Push Error: {e}")

def create_admin_notification(title, message, type="general", metadata=None):
    """Create a notification for admin panel"""
    try:
        db = get_db()
        notification_data = {
            'title': title,
            'message': message,
            'type': type,
            'read': False,
            'created_at': datetime.datetime.now(),
            'metadata': metadata or {}
        }

        db.collection('admin_notifications').add(notification_data)
        print(f"Admin notification created: {title}")
    except Exception as e:
        print(f"Error creating admin notification: {e}")

# TRIGGER IN YOUR VERIFY-PAYMENT ROUTE:
# send_push_notification(order_data['userId'], "Payment Received! 🌿", "We are preparing your fresh crops for delivery.")