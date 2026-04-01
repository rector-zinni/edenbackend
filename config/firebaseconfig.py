import os
import json
import firebase_admin
from firebase_admin import credentials

# This check prevents re-initializing the app if Vercel re-runs the script
if not firebase_admin._apps:
    # Look for the JSON content in an environment variable first
    cert_env = os.getenv('FIREBASE_CONFIG_JSON')
    
    if cert_env:
        # Use the string from Vercel Environment Variables
        cert_dict = json.loads(cert_env)
        cred = credentials.Certificate(cert_dict)
    else:
        # Fallback for your local Kali machine
        path = "config/theneweden-6dcba-firebase-adminsdk-fbsvc-c80f52499e.json"
        cred = credentials.Certificate(path)

    firebase_admin.initialize_app(cred, {
        'storageBucket': 'theneweden-6dcba.appspot.com' 
    })