from flask import Flask, request, jsonify
import requests
import re
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK")
DISCORD_FAIL_WEBHOOK = os.getenv("DISCORD_FAIL_WEBHOOK")

if not DISCORD_WEBHOOK or not DISCORD_FAIL_WEBHOOK:
    raise RuntimeError("Missing webhook(s) in .env file")

app = Flask(__name__)

# Regex: **username** (ID) joined the game.
pattern = re.compile(r"^\*\*[^\*]{1,30}\*\* \(ID: \d{1,15}\) joined the game\.$")

# Logging file (optional)
LOG_FILE = "fail_log.txt"

def send_to_discord(webhook_url, content):
    try:
        resp = requests.post(webhook_url, json={"content": content})
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ Discord error: {e}")
        return False

def log_failed_attempt(ip, content, headers):
    timestamp = datetime.utcnow().isoformat()
    user_agent = headers.get("User-Agent", "Unknown")
    forwarded_for = headers.get("X-Forwarded-For", "N/A")
    real_ip = headers.get("X-Real-IP", "N/A")
    referrer = headers.get("Referer", "N/A")
    content_type = headers.get("Content-Type", "N/A")

    log_entry = (
        f"[{timestamp} UTC]\n"
        f"IP: {ip}\n"
        f"X-Forwarded-For: {forwarded_for}\n"
        f"X-Real-IP: {real_ip}\n"
        f"User-Agent: {user_agent}\n"
        f"Referer: {referrer}\n"
        f"Content-Type: {content_type}\n"
        f"Raw Message:\n{content}\n---\n"
    )

    print("🚫 Logged failed attempt:\n" + log_entry)

    try:
        with open(LOG_FILE, "a") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"❌ Failed to write to log file: {e}")


@app.route("/", methods=["POST"])
def webhook_proxy():
    data = request.get_json()
    content = data.get("content") if data else None
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)

    if not isinstance(content, str) or not pattern.match(content):
        fail_message = (
            f"🚫 **Rejected message**\n"
            f"**IP:** `{ip}`\n"
            f"**Content:**\n```{content}```"
        )
        send_to_discord(DISCORD_FAIL_WEBHOOK, fail_message)
        log_failed_attempt(ip, content)
        return jsonify({"error": "Invalid message format"}), 400

    if send_to_discord(DISCORD_WEBHOOK, content):
        print("✅ Forwarded:", content)
        return jsonify({"success": True}), 200
    else:
        return jsonify({"error": "Failed to send to Discord"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)
