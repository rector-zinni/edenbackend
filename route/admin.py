from flask import Blueprint, jsonify
from firebase_admin import firestore, auth # Added auth for real user count
import datetime
from collections import defaultdict

admin_bp = Blueprint('admin', __name__)
db = firestore.client()

@admin_bp.route('/admin/analytics', methods=['GET'])
def get_analytics():
    try:
        # 1. GET REAL USER COUNT
        # We fetch the list of users from Firebase Auth
        user_pages = auth.list_users().iterate_all()
        total_users = sum(1 for _ in user_pages)

        # 2. INITIALIZE TRACKERS
        orders_ref = db.collection('orders')
        # We only care about confirmed sales for the dashboard
        paid_orders = orders_ref.where('payment_status', '==', 'paid').stream()
        
        total_revenue = 0
        total_orders = 0
        product_sales = {}
        monthly_stats = defaultdict(lambda: {"revenue": 0, "orders": 0})

        # 3. PROCESS ORDERS
        for doc in paid_orders:
            order = doc.to_dict()
            amount = order.get('totalAmount', 0)
            created_at = order.get('created_at') # This is a Firestore Timestamp

            total_revenue += amount
            total_orders += 1
            
            # --- Track Products ---
            for item in order.get('items', []):
                name = item.get('name', 'Unknown Product')
                qty = item.get('quantity') or item.get('qty') or 1
                price = item.get('price', 0)
                product_sales[name] = product_sales.get(name, 0) + (price * qty)

            # --- Group by Month for Charts ---
            if created_at:
                # Firestore Timestamps have a .month and .year if converted to datetime
                month_key = created_at.strftime('%b') # e.g., "Mar"
                monthly_stats[month_key]["revenue"] += amount
                monthly_stats[month_key]["orders"] += 1

        # 4. FORMAT TOP PRODUCTS
        sorted_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:5]
        # Avoid division by zero if no sales yet
        max_sales = sorted_products[0][1] if sorted_products else 1
        top_products = [
            {"name": n, "sales": s, "pct": (s/max_sales)*100} 
            for n, s in sorted_products
        ]

        # 5. FORMAT MONTHLY DATA FOR RECHARTS
        # This ensures the chart shows months in order
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        current_month_index = datetime.datetime.now().month
        visible_months = month_order[:current_month_index]

        formatted_monthly = []
        for m in visible_months:
            formatted_monthly.append({
                "month": m,
                "revenue": monthly_stats[m]["revenue"],
                "orders": monthly_stats[m]["orders"]
            })

        return jsonify({
            "totalRevenue": total_revenue,
            "totalOrders": total_orders,
            "totalUsers": total_users, # Real count from Firebase Auth
            "avgOrderValue": total_revenue / total_orders if total_orders > 0 else 0,
            "topProducts": top_products,
            "monthlyData": formatted_monthly
        })

    except Exception as e:
        print(f"Analytics Error: {str(e)}")
        return jsonify({"error": str(e)}), 500