# backend/address_bp.py
from flask import Blueprint, request, jsonify, g
from firebase_admin import firestore
from middleware.auth import verify_firebase_token
from service.send_email import send_eden_email

# Firestore client
db = firestore.client()

# Create Blueprint
address_bp = Blueprint("address", __name__)

# -----------------------------
# GET current user's address
# -----------------------------
@address_bp.route("/me/address", methods=["GET"])
@verify_firebase_token
def get_address():
    uid = g.user["uid"]
    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()
    send_eden_email('dd','lauramikemiller@gmail.com','jesus')

    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404

    user_data = user_doc.to_dict()
    address = user_data.get("address", {
        "street": "",
        "city": "",
        "state": "",
        "country": "Nigeria",
    })

    return jsonify({"address": address}), 200

# -----------------------------
# UPDATE current user's address
# -----------------------------
@address_bp.route("/me/address", methods=["PUT"])
@verify_firebase_token
def update_address():
    uid = g.user["uid"]
    data = request.json or {}

    street = data.get("street", "")
    city = data.get("city", "")
    state = data.get("state", "")
    country = data.get("country", "Nigeria")  # fixed default

    # Simple validation
    if not city or not state:
        return jsonify({"error": "City and state are required"}), 400

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()
    if not user_doc.exists:
        return jsonify({"error": "User not found"}), 404

    # Update only the address field
    user_ref.update({
        "address": {
            "street": street,
            "city": city,
            "state": state,
            "country": country
        },
        "updatedAt": firestore.SERVER_TIMESTAMP
    })

    return jsonify({"message": "Address updated successfully"}), 200
