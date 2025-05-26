from flask import Flask, request, jsonify
from agora_token_builder import RtcTokenBuilder
from google.cloud import firestore
import firebase_admin
from firebase_admin import credentials, auth
import time

app = Flask(__name__)

# 🔐 Your Agora credentials
APP_ID = "3501bf7b9ccf45eb91524782efc6e3dc"
APP_CERTIFICATE = "5567c6e7b55e416aab0a4739d5a7d522"

# 🔐 Firebase Admin Initialization
cred = credentials.Certificate("firebase-adminsdk.json")
firebase_admin.initialize_app(cred)
db = firestore.Client()

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

@app.route("/generate-token", methods=["POST"])
def generate_token():
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

    # 🔍 Check if user is student or teacher for this session
    try:
        student_session_ref = db.collection("users").document(uid).collection("sessionHistory").document(channel_name)
        student_session_doc = student_session_ref.get()

        if not student_session_doc.exists:
            return jsonify({"error": "User not authorized for this session"}), 403
    except Exception as e:
        print("❌ Firestore error:", e)
        return jsonify({"error": "Session validation failed"}), 500

    # ⏳ Token settings
    expire_seconds = 3600
    current_ts = int(time.time())
    privilege_expire_ts = current_ts + expire_seconds
    agora_role = 1 if role == "publisher" else 2

    # 🎟 Generate token
    token = RtcTokenBuilder.buildTokenWithUid(
        APP_ID, APP_CERTIFICATE, channel_name, int(uid), agora_role, privilege_expire_ts
    )

    return jsonify({ "token": token })

if __name__ == "__main__":
    app.run(debug=True)
