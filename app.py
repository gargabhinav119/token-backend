from flask import Flask, request, jsonify
from flask_cors import CORS
from agora_token_builder import RtcTokenBuilder
import time

app = Flask(__name__)

# ✅ Enable CORS for all origins and allow credentials (optional)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# 🔐 Agora credentials (replace with your actual credentials)
APP_ID = "3501bf7b9ccf45eb91524782efc6e3dc"
APP_CERTIFICATE = "5567c6e7b55e416aab0a4739d5a7d522"

# ✅ Root route (optional for testing)
@app.route("/", methods=["GET"])
def home():
    return "✅ Simple Token Generator Backend is Running!"

# 🎯 Token generation endpoint
@app.route("/generate-token", methods=["POST", "OPTIONS"])
def generate_token():
    # 🌐 CORS Preflight request handling
    if request.method == "OPTIONS":
        response = jsonify({"message": "CORS preflight OK"})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
        response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
        return response, 200

    try:
        # ✅ Parse incoming JSON body
        data = request.get_json()
        channel_name = data.get("channelName")
        uid = data.get("uid")
        role = data.get("role", "publisher")

        # 🛑 Check required fields
        if not channel_name or not uid:
            return jsonify({"error": "Missing channelName or uid"}), 400

        # ⏳ Token valid for 1 hour
        expire_seconds = 3600
        current_ts = int(time.time())
        privilege_expire_ts = current_ts + expire_seconds

        # 🎭 Agora role: 1 = publisher, 2 = subscriber
        agora_role = 1 if role == "publisher" else 2

        # 🪙 Generate token using uid (as account string)
        token = RtcTokenBuilder.buildTokenWithAccount(
            APP_ID,
            APP_CERTIFICATE,
            channel_name,
            uid,
            agora_role,
            privilege_expire_ts
        )

        # ✅ Return token
        return jsonify({ "token": token })

    except Exception as e:
        print("❌ Error generating token:", e)
        return jsonify({"error": "Internal server error"}), 500

# 🧪 Local development
if __name__ == "__main__":
    app.run(debug=True)
