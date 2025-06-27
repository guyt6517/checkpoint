from flask import Flask, request, jsonify
import requests
import re
import os
from dotenv import load_dotenv

# Load .env variables
load_dotenv()
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")

if not DISCORD_WEBHOOK:
    raise RuntimeError("Missing DISCORD_WEBHOOK in .env file")

app = Flask(__name__)

# Regex: **username** (ID) joined the game.
pattern = re.compile(r"^(\*\*)?[\w_]{3,20}(\*\*)? \(\d{1,15}\) joined the game\.$")

@app.route("/", methods=["POST"])
def webhook_proxy():
    data = request.get_json()
    content = data.get("content") if data else None

    if not isinstance(content, str) or not pattern.match(content):
        print("❌ Rejected message:", content)
        return jsonify({"error": "Invalid message format"}), 400

    try:
        response = requests.post(DISCORD_WEBHOOK, json={"content": content})
        response.raise_for_status()
        print("✅ Forwarded:", content)
        return jsonify({"success": True}), 200
    except Exception as e:
        print("❌ Discord error:", str(e))
        return jsonify({"error": "Failed to send to Discord"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
