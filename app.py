import os
import sys
import logging
import firebase_admin
from firebase_admin import firestore, auth, storage
from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps

# Import your custom extensions and routes
# Ensure these files are in your GitHub repository
from extensions import mail  
from middleware.auth import verify_firebase_token
from route.createuser import sync_user_bp
from route.add_product import admin_products
from route.get_product import products_bp
from route.updateUser import users_bp
from route.address import address_bp
from route.deliveryfee import delivery_bp
from route.payment import payment_bp
from route.order import orders_bp
from route.admin import admin_bp
from route.notification import notification_bp

# 1. Setup Logging
# Vercel captures stdout/stderr automatically. 
# Local FileHandlers are removed to prevent "Read-only file system" errors.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

app = Flask(__name__)

# Enable CORS so your Expo app can communicate with this API
CORS(app)

# 2. Mail Configuration
# It's best practice to use environment variables for passwords on Vercel
app.config['MAIL_SERVER'] = 'mail.privateemail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME', 'support@moamudipefoundation.org')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD', 'Rector-99') 
app.config['MAIL_DEFAULT_SENDER'] = ('The New Eden', app.config['MAIL_USERNAME'])

# Initialize Mailer
mail.init_app(app)

# 3. Firebase Setup
# Ensure your 'config.firebaseconfig' handles initialization correctly for production
import config.firebaseconfig
db = firestore.client()
bucket = storage.bucket()

@app.route('/')
def home():
    return jsonify({
        "status": "The New Eden API running", 
        "platform": "Vercel Serverless",
        "database": "Connected to Firestore",
        "messaging": "Mail System Active"
    })

# Protected route example for your Expo App
@app.route('/api/cart', methods=['GET'])
@verify_firebase_token
def get_cart():
    user_id = getattr(request, 'user_id', None)
    cart = [
        {"item": "Fresh Tomatoes", "qty": 3},
        {"item": "Organic Bananas", "qty": 5}
    ]
    return jsonify({"user_id": user_id, "cart": cart})

# Test email route
@app.route('/api/test-email', methods=['POST'])
def test_email():
    data = request.json
    recipient = data.get('email', 'showolesheriff10@gmail.com')
    subject = 'Test Email from Eden Backend'
    body = '<p>This is a test email to verify SMTP configuration.</p>'
    
    try:
        from service.send_email import send_eden_email
        success, message = send_eden_email(subject, recipient, body)
        if success:
            return jsonify({"status": "Email sent", "message": message}), 200
        else:
            return jsonify({"status": "Failed", "message": message}), 500
    except Exception as e:
        logging.error(f"Email error: {str(e)}")
        return jsonify({"status": "Error", "message": str(e)}), 500

# 4. Register Blueprints
app.register_blueprint(sync_user_bp, url_prefix="/api")
app.register_blueprint(admin_products, url_prefix="/api")
app.register_blueprint(products_bp, url_prefix="/api")
app.register_blueprint(users_bp, url_prefix="/api")
app.register_blueprint(address_bp, url_prefix="/api/users")
app.register_blueprint(payment_bp, url_prefix="/api")
app.register_blueprint(orders_bp, url_prefix="/api")
app.register_blueprint(delivery_bp, url_prefix="/api")
app.register_blueprint(admin_bp, url_prefix="/api")
app.register_blueprint(notification_bp, url_prefix="/api")

# Vercel uses the 'app' object directly. 
# The block below is only used for your local development.
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=False)