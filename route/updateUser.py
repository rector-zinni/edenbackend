from flask import Blueprint, request, jsonify, g
from firebase_admin import firestore
from middleware.auth import verify_firebase_token

users_bp = Blueprint("users", __name__)
db = firestore.client()

# Get current user
@users_bp.route("/users", methods=["GET"])
@verify_firebase_token
def get_user():
    try:
        uid = g.user["uid"]
        print("GET /api/users called by uid:", uid)
        if not uid:
            return jsonify({"error": "Unauthorized"}), 401

        doc = db.collection("users").document(uid).get()
        if not doc.exists:
            return jsonify({"error": "User not found"}), 404
        return jsonify(doc.to_dict()), 200
    except Exception as e:
        print("GET /api/users error:", e)
        return jsonify({"error": str(e)}), 500

# Update current user
@users_bp.route("/users", methods=["PUT"])
@verify_firebase_token
def update_user():
    try:
        data = request.get_json()
        uid = g.user["uid"]
        if not uid:
            return jsonify({"error": "Unauthorized"}), 401

        db.collection("users").document(uid).update({
            "fullName": data.get("fullName"),
            "email": data.get("email"),
            "phoneNumber": data.get("phoneNumber"),
            "state": data.get("state"),
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "photoURL": data.get("photoURL")
        })

        return jsonify({"message": "User updated successfully"}), 200
    except Exception as e:
        print("PUT /api/users error:", e)
        return jsonify({"error": str(e)}), 500


# Get all users (Admin Only)
@users_bp.route("/users/all", methods=["GET"])
def get_all_users():
    try:
        # 1. Optional Security Check: Ensure the requester is an admin
        # You can check this via a custom claim or a field in their Firestore doc

        # 2. Fetch all clients
        users_ref = db.collection("users")
        # You might want to filter by 'role': 'customer' if you have different types
        docs = users_ref.stream()

        all_users = []
        for doc in docs:
            user_data = doc.to_dict()
            user_data["id"] = doc.id  # Include the document ID
            
            # Convert Firestore timestamps to strings for JSON compatibility
            if "createdAt" in user_data and user_data["createdAt"]:
                user_data["createdAt"] = user_data["createdAt"].isoformat()
            if "updatedAt" in user_data and user_data["updatedAt"]:
                user_data["updatedAt"] = user_data["updatedAt"].isoformat()
                
            all_users.append(user_data)

        print(f"Fetched {len(all_users)} users for admin")
        return jsonify({"status": True, "users": all_users}), 200

    except Exception as e:
        print("GET /api/users/all error:", e)
        return jsonify({"error": str(e)}), 500