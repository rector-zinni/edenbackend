from flask import Blueprint, request, jsonify, g
from firebase_admin import firestore
import datetime
import logging
from service.notification import send_push_notification
from service.send_email import send_eden_email
from service.email_template import get_welcome_template

from middleware.auth import verify_firebase_token

orders_bp = Blueprint('orders', __name__)
db = firestore.client()
logger = logging.getLogger(__name__)

# --- HELPER: DATE FORMATTER ---
def format_dates(order_dict):
    """Converts Firestore timestamps to ISO strings for React/Expo."""
    if 'created_at' in order_dict and order_dict['created_at']:
        try:
            order_dict['created_at'] = order_dict['created_at'].isoformat()
        except AttributeError:
            pass
    if 'updated_at' in order_dict and order_dict['updated_at']:
        try:
            order_dict['updated_at'] = order_dict['updated_at'].isoformat()
        except AttributeError:
            pass
    return order_dict

# --- 1. CREATE ORDER (SILENT) ---
@orders_bp.route('/create-order', methods=['POST'])
@verify_firebase_token
def save_order():
    try:
        data = request.json
        uid = g.user['uid']
        
        # Payload starts as 'processing' or 'pending'
        order_payload = {
            "userId": uid, 
            "user_email": data.get("user_email"),
            "phone_number": data.get("phoneNumber"),
            "items": data.get("orderItems"), 
            "subtotal": data.get("subtotal"),
            "delivery_fee": data.get("deliveryFee"),
            "totalAmount": data.get("totalAmount"),
            "currency": data.get("currency", "NGN"),
            "payment_reference": data.get("paymentReference"),
            "payment_provider": data.get("payment_provider", "paystack"),
            "payment_status": "processing", # Email is NOT sent yet
            "shipping_address": data.get("shippingAddress"),
            "status": "Awaiting Payment", 
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now(),
        }

        # Save to Firestore
        _, doc_ref = db.collection('orders').add(order_payload)
        
        return jsonify({
            "status": True, 
            "message": "Order created. Awaiting payment verification.",
            "order_id": doc_ref.id
        }), 201

    except Exception as e:
        logger.error(f"Order Creation Failure: {e}")
        return jsonify({"status": False, "message": str(e)}), 500

# --- 1.B CREATE GUEST ORDER (SILENT) ---
@orders_bp.route('/guest/create-order', methods=['POST'])
def save_guest_order():
    try:
        data = request.json
        uid = data.get("userId") # e.g. "guest_<UUID>"
        
        order_payload = {
            "userId": uid, 
            "user_email": data.get("user_email"),
            "phone_number": data.get("phoneNumber"),
            "items": data.get("orderItems"), 
            "subtotal": data.get("subtotal"),
            "delivery_fee": data.get("deliveryFee"),
            "totalAmount": data.get("totalAmount"),
            "currency": data.get("currency", "NGN"),
            "payment_reference": data.get("paymentReference"),
            "payment_provider": data.get("payment_provider", "paystack"),
            "payment_status": "processing",
            "shipping_address": data.get("shippingAddress"),
            "status": "Awaiting Payment", 
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now(),
            "is_guest": True,
        }

        # Save to Firestore
        _, doc_ref = db.collection('orders').add(order_payload)
        
        return jsonify({
            "status": True, 
            "message": "Guest Order created. Awaiting payment.",
            "order_id": doc_ref.id
        }), 201

    except Exception as e:
        logger.error(f"Guest Order Creation Failure: {e}")
        return jsonify({"status": False, "message": str(e)}), 500

# --- 2. GET USER ORDER HISTORY ---
@orders_bp.route('/order-history', methods=['GET'])
@verify_firebase_token
def get_user_orders():
    try:
        user_id = g.user['uid']
        
        orders_query = db.collection('orders')\
            .where('userId', '==', user_id)\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .stream()

        orders_list = []
        for doc in orders_query:
            order_data = doc.to_dict()
            order_data['id'] = doc.id
            orders_list.append(format_dates(order_data))

        return jsonify({"status": True, "orders": orders_list}), 200
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500

# --- 3. GET SINGLE ORDER ---
@orders_bp.route('/order/<order_id>', methods=['GET'])
@verify_firebase_token
def get_single_order(order_id):
    try:
        user_id = g.user['uid']
        doc_ref = db.collection('orders').document(order_id).get()

        if not doc_ref.exists:
            return jsonify({"status": False, "message": "Order not found"}), 404

        order = doc_ref.to_dict()
        if order.get("userId") != user_id:
            return jsonify({"status": False, "message": "Unauthorized"}), 403

        order["id"] = doc_ref.id
        return jsonify({"status": True, "order": format_dates(order)}), 200
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500



# --- 4. ADMIN: UPDATE ORDER STATUS ---
@orders_bp.route('/admin/order/<order_id>/status', methods=['PATCH'])
def update_order_status(order_id):
    try:
        data = request.json
        new_status = data.get('status') # e.g., "Out for Delivery"
        
        if not new_status:
            return jsonify({"status": False, "message": "No status provided"}), 400

        order_ref = db.collection('orders').document(order_id)
        order_doc = order_ref.get()

        if not order_doc.exists:
            return jsonify({"status": False, "message": "Order not found"}), 404
        
        order_data = order_doc.to_dict()
        user_id = order_data.get('userId')

        print(f"DEBUG: Updating order {order_id} to {new_status}, user_id: {user_id}")  # Debug

        # Update Firestore
        order_ref.update({
            "status": new_status,
            "updated_at": datetime.datetime.now()
        })

        # --- THE PUSH NOTIFICATION & EMAIL ---
        # Logic: Notify the user that their order status has changed
        if user_id:
            print(f"DEBUG: User ID found: {user_id}, proceeding with notifications")  # Debug
            title = "Eden Order Update 🌿"
            body = f"Your order #{order_id[-6:].upper()} is now: {new_status}"

            # Send in-app push notification if token exists
            send_push_notification(user_id, title, body)

            # Send email update - check order document first (for guests), then user document (for registered users)
            recipient_email = order_data.get('user_email')  # Email from order (works for both guest and registered)
            recipient_name = 'Eden Customer'
            
            # Try to get more details from user document if it exists
            user_doc = db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                # Use user document email if available and order email is missing
                if not recipient_email:
                    recipient_email = user_data.get('email')
                recipient_name = user_data.get('fullName', 'Eden Customer')

            print(f"DEBUG: Recipient email from order/user: {recipient_email}")  # Debug

            if recipient_email:
                email_subject = "Your order status has changed"
                email_body = f"<p>Hi {recipient_name},</p><p>Your order <strong>#{order_id[-6:].upper()}</strong> is now: <strong>{new_status}</strong>.</p><p>Thank you for choosing Eden!</p>"
                print(f"DEBUG: Sending email to {recipient_email} for order {order_id}")  # Debug
                try:
                    send_eden_email(email_subject, recipient_email, email_body)
                    print(f"DEBUG: Email send function called successfully")  # Debug
                except Exception as e:
                    logger.warning(f"Failed to send status email to {recipient_email}: {e}")
                    print(f"DEBUG: Email send failed: {e}")  # Debug
            else:
                print(f"DEBUG: No email found for user {user_id} or order {order_id}")  # Debug

        return jsonify({
            "status": True, 
            "message": f"Order updated to {new_status} and user notified."
        }), 200

    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500

# --- 5. ADMIN: GET ALL ORDERS ---
@orders_bp.route('/admin/order-history', methods=['GET'])
def get_all_orders_as_admin():
    try:
        orders_query = db.collection('orders')\
            .order_by('created_at', direction=firestore.Query.DESCENDING)\
            .stream()

        orders_list = []
        for doc in orders_query:
            order_data = doc.to_dict()
            order_data['id'] = doc.id
            orders_list.append(format_dates(order_data))

        return jsonify({"status": True, "orders": orders_list}), 200
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500

# --- 6. GUEST: TRACK ORDER (POST) ---
@orders_bp.route('/guest/track-order', methods=['POST'])
def track_guest_order():
    try:
        data = request.json
        order_id = data.get("orderId")
        email = data.get("email")
        logger.info(f"🔍 Guest tracking attempt: order_id='{order_id}', email='{email}'")
        
        if not order_id or not email:
            logger.warning(f"❌ Missing credentials: orderId={order_id}, email={email}")
            return jsonify({"status": False, "message": "Missing credentials"}), 400

        # Try direct ID first
        doc_ref = db.collection('orders').document(order_id).get()
        
        # If not found, try with guest_ prefix
        if not doc_ref.exists and not order_id.startswith('guest_'):
            logger.info(f"⚠️  Order '{order_id}' not found, trying with 'guest_' prefix...")
            doc_ref = db.collection('orders').document(f"guest_{order_id}").get()
            if doc_ref.exists:
                logger.info(f"✅ Found with prefix: guest_{order_id}")
                order_id = f"guest_{order_id}"
        
        if not doc_ref.exists:
            logger.warning(f"❌ Order not found: '{order_id}' (checked both with and without 'guest_' prefix)")
            return jsonify({"status": False, "message": "Order not found"}), 404
            
        order = doc_ref.to_dict()
        stored_email = order.get("user_email")
        logger.info(f"📦 Order found. stored_email='{stored_email}', provided_email='{email}'")
        
        if stored_email != email:
            logger.warning(f"❌ Email mismatch: provided='{email}', stored='{stored_email}'")
            return jsonify({"status": False, "message": "Invalid email for this order"}), 403

        order["id"] = doc_ref.id
        logger.info(f"✅ Guest order '{order_id}' retrieved successfully for {email}")
        return jsonify({"status": True, "order": format_dates(order)}), 200

    except Exception as e:
        logger.error(f"🔥 Guest Order Tracking Error: {e}", exc_info=True)
        return jsonify({"status": False, "message": str(e)}), 500