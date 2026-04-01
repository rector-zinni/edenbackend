from functools import wraps
from flask import request, jsonify,g
from firebase_admin import auth

def verify_firebase_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return jsonify({"error": "Authorization header missing"}), 401
        #strip 'Bearer if present
        try:
            token = auth_header.split(" ")[1]  # Remove "Bearer"
            decoded_token = auth.verify_id_token(token)
            g.user = decoded_token  # ← this is the crucial line
        except Exception as e:
            return jsonify({"error": "Invalid or expired token"}), 401

        return f(*args, **kwargs)

    return decorated_function
