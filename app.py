from flask import Flask, request, jsonify
from flask_cors import CORS
from agora_token_builder import RtcTokenBuilder
from google.cloud import firestore
from google.oauth2 import service_account
import firebase_admin
from firebase_admin import credentials, auth
import time

app = Flask(__name__)
CORS(app, origins="*", supports_credentials=True)

# 🔐 Agora credentials
APP_ID = "3501bf7b9ccf45eb91524782efc6e3dc"
APP_CERTIFICATE = "5567c6e7b55e416aab0a4739d5a7d522"

# 🔐 Firebase Admin Initialization
cred = credentials.Certificate("firebase-adminsdk.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# 🔐 Firestore client
gcp_credentials = service_account.Credentials.from_service_account_file("firebase-adminsdk.json")
db = firestore.Client(credentials=gcp_credentials, project=gcp_credentials.project_id)

# 🏥 Root route (for testing)
@app.route("/", methods=["GET"])
def index():
    return "✅ Token backend is running!"

# 🔐 Firebase ID Token Verification
def verify_firebase_user():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None
    id_token = auth_header.split(" ")[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        print("❌ Firebase Auth Failed:", e)
        return None

# 🎯 Token Generation Endpoint
@app.route("/generate-token", methods=["GET", "POST", "OPTIONS"])
def generate_token():
    if request.method == "OPTIONS":
        return jsonify({"message": "CORS Preflight OK ✅"}), 200

    if request.method == "GET":
        return jsonify({"message": "Token route is live ✅ Use POST to generate token."}), 200

    # Handle POST
    user = verify_firebase_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    channel_name = data.get("channelName")
    uid = data.get("uid")
    role = data.get("role", "publisher")

    if not channel_name or not uid:
        return jsonify({"error": "Missing channelName or uid"}), 400

    if user["uid"] != uid:
        return jsonify({"error": "UID mismatch"}), 403

    # 🔎 Check if session exists
    try:
        session_ref = db.collection("users").document(uid).collection("sessionHistory").document(channel_name)
        session_doc = session_ref.get()
        if not session_doc.exists:
            return jsonify({"error": "User not authorized for this session"}), 403
    except Exception as e:
        print("❌ Firestore error:", e)
        return jsonify({"error": "Session validation failed"}), 500

    # ⏳ Token valid for 3 minutes
    expire_seconds = 180
    current_ts = int(time.time())
    privilege_expire_ts = current_ts + expire_seconds
    agora_role = 1 if role == "publisher" else 2

    # 🎫 Generate token
    token = RtcTokenBuilder.buildTokenWithAccount(
        APP_ID, APP_CERTIFICATE, channel_name, uid, agora_role, privilege_expire_ts
    )


    return jsonify({"token": token})

# 🔧 Local only
if __name__ == "__main__":
    app.run(debug=True)
