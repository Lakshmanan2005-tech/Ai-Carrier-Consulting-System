import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
from dotenv import load_dotenv

# Load .env variables immediately at import time
load_dotenv(override=True)

# Firebase Service Account Certificate Path (Hardcoded fallback)
CERT_FILENAME = 'ai-carrier-consulting-system-firebase-adminsdk-fbsvc-a35be6ef24.json'
CERT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), CERT_FILENAME)

def initialize_firebase():
    """Initializes the Firebase Admin SDK and returns a Firestore client."""
    if not firebase_admin._apps:
        creds_env = os.getenv('FIREBASE_CREDENTIALS')
        
        try:
            if creds_env:
                # 1. Check if it's direct JSON content (starts with {)
                if creds_env.strip().startswith('{'):
                    print("[-] Initializing Firebase from JSON content in .env")
                    cred = credentials.Certificate(json.loads(creds_env))
                # 2. Otherwise assume it's a file path
                else:
                    print(f"[-] Initializing Firebase from file path: {creds_env}")
                    cred = credentials.Certificate(creds_env)
            else:
                # 3. Fallback to hardcoded JSON path
                if not os.path.exists(CERT_PATH):
                    # We print warning instead of raising immediately to allow local debugging if needed
                    # but since the system requires it, we still raise if everything fails
                    raise FileNotFoundError(f"Missing FIREBASE_CREDENTIALS in .env and file not found at: {CERT_PATH}")
                print(f"[-] Initializing Firebase from hardcoded JSON path: {CERT_PATH}")
                cred = credentials.Certificate(CERT_PATH)
            
            firebase_admin.initialize_app(cred)
            print("[+] Firebase Admin SDK initialized successfully.")
        except Exception as e:
            print(f"[!] Firebase Initialization Error: {e}")
            raise e
    
    return firestore.client()

# Global Firestore database instance
db = initialize_firebase()
