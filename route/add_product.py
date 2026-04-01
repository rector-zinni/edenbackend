from flask import Blueprint, request, jsonify
from firebase_admin import firestore
import uuid
import random
import string
from service.notification import create_admin_notification

admin_products = Blueprint("admin_products", __name__)
db = firestore.client()


def generate_sku(category, name, unit):
    cat_code = category[:3].upper()
    prod_code = "".join([word[0] for word in name.split()][:3]).upper()
    unit_code = unit.upper().replace(" ", "")
    rand = "".join(random.choices(string.digits, k=3))
    return f"{cat_code}-{prod_code}-{unit_code}-{rand}"


@admin_products.route("/admin/products", methods=["POST"])
def create_or_update_product():
    try:
        data = request.json

        incoming_id = data.get("id")
        is_update = bool(incoming_id)

        name = data.get("name")
        category = data.get("category")
        unit = data.get("unit")
        stock = data.get("stock", 0)
        description = data.get("description", "")
        promo_percent = data.get("promoPercent", 0)
        featured_promo = data.get("featuredPromo", False)

        prices = data.get("prices", {})
        images = data.get("images", [])

        # --------------------
        # Validation
        # --------------------

        if not name:
            return jsonify({"message": "Product name required"}), 400

        if not category:
            return jsonify({"message": "Category required"}), 400

        if not unit:
            return jsonify({"message": "Unit required"}), 400

        if promo_percent < 0 or promo_percent > 100:
            return jsonify({"message": "Promo must be 0-100"}), 400

        if not prices:
            return jsonify({"message": "At least one state price required"}), 400

        if len(images) > 4:
            return jsonify({"message": "Maximum of 4 images allowed"}), 400

        batch = db.batch()

        # --------------------
        # UPDATE PRODUCT
        # --------------------

        if is_update:

            product_ref = db.collection("products").document(incoming_id)
            doc = product_ref.get()

            if not doc.exists:
                return jsonify({"message": "Product not found"}), 404

            existing_data = doc.to_dict()

            # Add stock instead of overwriting
            total_stock = existing_data.get("stock", 0) + stock

            # Merge state prices
            merged_prices = {
                **existing_data.get("prices", {}),
                **prices
            }

            batch.update(product_ref, {
                "name": name,
                "stock": total_stock,
                "prices": merged_prices,
                "description": description,
                "promoPercent": promo_percent,
                "hasPromo": promo_percent > 0,
                "featuredPromo": featured_promo,
                "images": images,  # FULL REPLACEMENT (frontend controls it)
                "category": category,
                "unit": unit,
                "updatedAt": firestore.SERVER_TIMESTAMP
            })

            product_id = incoming_id
            sku = existing_data.get("sku")

        # --------------------
        # CREATE PRODUCT
        # --------------------

        else:

            product_id = uuid.uuid4().hex
            sku = generate_sku(category, name, unit)

            product_ref = db.collection("products").document(product_id)

            batch.set(product_ref, {
                "id": product_id,
                "sku": sku,
                "name": name,
                "category": category,
                "unit": unit,
                "stock": stock,
                "description": description,
                "promoPercent": promo_percent,
                "hasPromo": promo_percent > 0,
                "featuredPromo": featured_promo,
                "isActive": True,
                "images": images,
                "prices": prices,
                "createdAt": firestore.SERVER_TIMESTAMP
            })

        batch.commit()

        # Create notification for product operation
        operation_type = "updated" if is_update else "created"
        create_admin_notification(
            title=f"Product {operation_type.capitalize()}",
            message=f"{name} ({sku}) has been {operation_type}",
            type="product_operation",
            metadata={
                "product_id": product_id,
                "product_name": name,
                "sku": sku,
                "operation": operation_type,
                "category": category
            }
        )

        return jsonify({
            "message": "Product updated" if is_update else "Product created",
            "productId": product_id,
            "sku": sku
        }), 200 if is_update else 201

    except Exception as e:
        print("Error:", e)
        return jsonify({"message": "Server error"}), 500


@admin_products.route("/admin/products/<product_id>", methods=["DELETE"])
def delete_product(product_id):

    try:

        ref = db.collection("products").document(product_id)
        doc = ref.get()

        if not doc.get().exists:
            return jsonify({"message":"Product not found"}),404

        product_data = doc.to_dict()
        product_name = product_data.get("name", "Unknown Product")
        sku = product_data.get("sku", "Unknown SKU")

        ref.delete()

        # Create notification for product deletion
        create_admin_notification(
            title="Product Deleted",
            message=f"{product_name} ({sku}) has been deleted",
            type="product_operation",
            metadata={
                "product_id": product_id,
                "product_name": product_name,
                "sku": sku,
                "operation": "deleted"
            }
        )

        return jsonify({
            "message":"Product deleted"
        }),200

    except Exception as e:
        print(e)
        return jsonify({"message":"Server error"}),500