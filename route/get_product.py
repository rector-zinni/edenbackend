from flask import Blueprint, jsonify
from firebase_admin import firestore

# Blueprint for product retrieval
products_bp = Blueprint("products", __name__)
db = firestore.client()


@products_bp.route("/products", methods=["GET"])
def list_products():
    """Return a list of active products with prices."""
    try:
        docs = db.collection("products").where("isActive", "==", True).stream()
        items = []

        for doc in docs:
            product = doc.to_dict()
           
            items.append(product)

        return jsonify(items), 200
    except Exception as e:
        print("Error listing products:", e)
        return jsonify({"message": "Server error"}), 500


@products_bp.route("/products/<product_id>", methods=["GET"])
def get_product(product_id):
    """Return a single product by its ID with prices."""
    try:
        doc = db.collection("products").document(product_id).get()
        if not doc.exists:
            return jsonify({"message": "Product not found"}), 404

        product = doc.to_dict() or {}

    
        
        # Optional: serialize timestamp
        if product.get("createdAt"):
            product["createdAt"] = product["createdAt"].isoformat()

        return jsonify(product), 200
    except Exception as e:
        print("Error fetching product:", e)
        return jsonify({"message": "Server error"}), 500