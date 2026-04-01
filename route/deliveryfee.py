# route/delivery.py
from flask import Blueprint, request, jsonify
from math import radians, sin, cos, sqrt, atan2

delivery_bp = Blueprint("delivery", __name__)

# Warehouse coordinates (example: Lagos)
WAREHOUSE_LAT = 6.5244
WAREHOUSE_LNG = 3.3792

# Static fee for MVP
STATIC_DELIVERY_FEE = 1000

# Optional: per km rate for future dynamic calculation
PER_KM_RATE = 500

# Haversine formula to calculate distance between two points
def calculate_distance_km(lat1, lng1, lat2, lng2):
    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlon = radians(lng2 - lng1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

@delivery_bp.route("/delivery-fee", methods=["POST"])
def delivery_fee():
    """
    Expects JSON:
    {
        "lat": float, // user latitude
        "lng": float  // user longitude
    }
    """
    data = request.json or {}
    user_lat = data.get("lat")
    user_lng = data.get("lng")

    if user_lat is None or user_lng is None:
        return jsonify({"error": "Latitude and longitude required"}), 400

    # Calculate distance (optional, for future)
    distance_km = calculate_distance_km(WAREHOUSE_LAT, WAREHOUSE_LNG, user_lat, user_lng)
    fee = STATIC_DELIVERY_FEE  # For MVP, keep it static
    # Uncomment below later for dynamic fee
    fee = STATIC_DELIVERY_FEE + (distance_km * PER_KM_RATE)

    return jsonify({
        "delivery_fee": int(fee),
        "distance_km": round(distance_km, 2)
    }), 200