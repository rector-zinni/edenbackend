# routes/payment.py
import requests
import os
from flask import Blueprint, request, jsonify, g
from firebase_admin import firestore
import datetime
from service.email_template import get_order_template, get_admin_payment_confirmed_template
from service.send_email import send_eden_email
import os
from service.notification import create_admin_notification
from config.env_loader import load_env_file
db = firestore.client()

load_env_file()
payment_bp = Blueprint("payment", __name__)
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

@payment_bp.route("/initialize-payment", methods=["POST"])
def initialize_payment():
    data = request.json
    email = data.get("email")
    amount = data.get("amount") # Must be Kobo
    # Support dynamic callback for web vs mobile
    callback_url = data.get("callback_url", "https://standard.paystack.co/close")

    if not email or not amount:
        return jsonify({"status": False, "message": "Missing email or amount"}), 400

    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "email": email,
        "amount": amount,
        "callback_url": callback_url
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"status": False, "message": str(e)}), 500





@payment_bp.route("/verify-payment", methods=["POST"])
def verify_payment():
    try:
        data = request.json
        reference = data.get("reference")
        order_id = data.get("orderId") 
        user_email = data.get("email")

        if not reference:
            return jsonify({"status": False, "message": "No reference provided"}), 400

        # 1. Paystack Verification Call
        url = f"https://api.paystack.co/transaction/verify/{reference}"
        headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
        response = requests.get(url, headers=headers)
        result = response.json()

        paystack_data = result.get("data")
        
        # 2. Check if Paystack confirms success
        if paystack_data and paystack_data.get("status") == "success":
            print(f"✅ Verified successfully: {reference}")
            
            if order_id:
                try:
                    order_ref = db.collection('orders').document(order_id)
                    order_doc = order_ref.get()

                    if not order_doc.exists:
                         return jsonify({"status": False, "message": "Order record not found"}), 404
                    
                    order_data = order_doc.to_dict()

                    # 3. SECURE DATABASE UPDATE
                    order_ref.update({
                        "payment_status": "paid",
                        "status": "Processing",
                        "payment_reference": reference,
                        "updated_at": datetime.datetime.now()
                    })

                    # 4. CREATE ADMIN NOTIFICATION FOR NEW ORDER
                    create_admin_notification(
                        title="New Order Received",
                        message=f"Order #{order_id[-6:].upper()} - ₦{order_data.get('totalAmount', 0):,.0f}",
                        type="new_order",
                        metadata={
                            "order_id": order_id,
                            "amount": order_data.get("totalAmount", 0),
                            "user_email": user_email,
                            "items_count": len(order_data.get("items", []))
                        }
                    )

                    # 5. 🔥 THE MAGIC: TRIGGER EMAIL NOW
                    user_email = order_data.get("user_email")
                    if user_email:
                        # Generate the professional template
                        html_content = get_order_template(
                            user_name=order_data.get("fullName") or order_data.get("user_email"),
                            order_id=order_id,
                            amount=order_data.get("totalAmount"),
                            items=order_data.get("items")
                        )
                        
                        # Send it! (Background thread ensures this is fast)
                        send_eden_email(
                            subject=f"Payment Received! Your Eden Order #{order_id[-6:].upper()} is Confirmed 🌿",
                            recipient=user_email,
                            body_html=html_content
                        )
                        # Notify admin about payment confirmation
                        try:
                            support_inbox = os.getenv('SUPPORT_INBOX', os.getenv('MAIL_USERNAME'))
                            if support_inbox:
                                admin_html = get_admin_payment_confirmed_template(
                                    order_id=order_id,
                                    user_email=user_email,
                                    total_amount=order_data.get('totalAmount', 0),
                                    items=order_data.get('items', []),
                                    payment_reference=reference
                                )
                                admin_subject = f"Payment Confirmed — Order #{order_id[-6:].upper()}"
                                send_eden_email(admin_subject, support_inbox, admin_html)
                        except Exception as _:
                            pass
                    
                    return jsonify({
                        "status": True,
                        "message": "Payment verified and order activated",
                        "order_id": order_id
                    }), 200
                except Exception as db_error:
                    print(f"Firestore Update Error: {db_error}")
                    return jsonify({"status": False, "message": "Payment ok, but failed to update order record."}), 500
            else:
                return jsonify({"status": False, "message": "Order ID missing from request"}), 400

        return jsonify({"status": False, "message": result.get("message", "Verification failed")}), 400

    except Exception as e:
        print(f"Internal Crash: {str(e)}")
        return jsonify({"status": False, "message": "Internal Server Error"}), 500