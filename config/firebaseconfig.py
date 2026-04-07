import os
import json
import ast
import firebase_admin
from firebase_admin import credentials
from config.env_loader import load_env_file

load_env_file()


def _load_certificate_from_env(cert_env):
    try:
        cert_dict = json.loads(cert_env)
    except json.JSONDecodeError:
        cert_dict = ast.literal_eval(cert_env)

    private_key = cert_dict.get('private_key')
    if isinstance(private_key, str):
        cert_dict['private_key'] = private_key.replace('\\n', '\n')

    return credentials.Certificate(cert_dict)


# This check prevents re-initializing the app if Vercel re-runs the script
if not firebase_admin._apps:
    # Look for the JSON content in an environment variable first
    cert_env = os.getenv('FIREBASE_CONFIG_JSON')
    
    if cert_env:
        # Use the string from Vercel Environment Variables
        try:
            cred = _load_certificate_from_env(cert_env)
        except (ValueError, SyntaxError, json.JSONDecodeError):
            path = "config/theneweden-6dcba-firebase-adminsdk-fbsvc-c80f52499e.json"
            cred = credentials.Certificate(path)
    else:
        # Fallback for your local Kali machine
        path = "config/theneweden-6dcba-firebase-adminsdk-fbsvc-c80f52499e.json"
        cred = credentials.Certificate(path)

    firebase_admin.initialize_app(cred, {
        'storageBucket': 'theneweden-6dcba.appspot.com' 
    })