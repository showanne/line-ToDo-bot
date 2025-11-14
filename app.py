# app.py (Flask + line-bot-sdk v3)
import os
from flask import Flask, request, abort, jsonify
from dotenv import load_dotenv
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.messaging.models import ReplyMessageRequest, TextMessage as V3TextMessage

# WebhookParser 在不同小版本 docs 路徑可能不同 -> 用 try/except 兼容
try:
    from linebot.v3.webhook import WebhookParser
except Exception:
    from linebot.v3.webhooks import WebhookParser

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("請在 .env 設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

app = Flask(__name__)
parser = WebhookParser(channel_secret=CHANNEL_SECRET)

# -----------------------------
# Helper function: 回覆訊息
# -----------------------------
def reply_line(reply_token: str, text: str):
    try:
        with ApiClient(Configuration(access_token=CHANNEL_ACCESS_TOKEN)) as api_client:
            messaging_api = MessagingApi(api_client)
            req = ReplyMessageRequest(
                reply_token=reply_token,
                messages=[V3TextMessage(type="text", text=text)]
            )
            messaging_api.reply_message(req)
    except Exception as e:
        app.logger.error("Failed to reply message: %s", e)

# -----------------------------
# Health check
# -----------------------------
@app.get("/health")
def health():
    return jsonify({"status": "ok"})

# -----------------------------
# LINE Webhook
# -----------------------------
@app.post("/callback")
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    app.logger.debug("LINE Webhook body: %s", body)

    try:
        events = parser.parse(body, signature)
    except Exception as e:
        app.logger.error("Webhook parse/signature failed: %s", e)
        abort(400, f"Invalid signature or parse error: {e}")

    for event in events:
        ev_type = getattr(event, "type", None)

        # ----------- Message event -----------
        if ev_type == "message":
            msg = getattr(event, "message", None)
            reply_token = getattr(event, "reply_token", None)
            if not reply_token:
                continue

            text = getattr(msg, "text", None) if msg else None
            if text is None:
                reply_line(reply_token, "我目前只處理文字訊息，請傳文字給我。")
                continue

            t = text.strip().lower()
            if t == "ping":
                reply_line(reply_token, "pong")
            elif t.startswith("echo "):
                reply_line(reply_token, text[5:].strip())
            elif t == "help":
                reply_line(reply_token, "指令：help / ping / echo <文字>")
            else:
                reply_line(reply_token, f"收到：{text}")

        # ----------- Follow event -----------
        elif ev_type == "follow":
            reply_token = getattr(event, "reply_token", None)
            if reply_token:
                reply_line(reply_token, "謝謝你加我為好友！輸入 help 查看指令。")

        # ----------- 其他事件 -----------
        else:
            app.logger.debug("Unhandled event type: %s", ev_type)

    return "OK", 200

# -----------------------------
# Main
# -----------------------------
if __name__ == "__main__":
    debug_mode = True
    port = int(os.getenv("PORT", 5000))

    # ngrok (只啟動一次)
    if debug_mode:
        try:
            from pyngrok import ngrok
            ngrok_authtoken = os.getenv("NGROK_AUTHTOKEN")
            if ngrok_authtoken:
                ngrok.set_auth_token(ngrok_authtoken)
            public_url = ngrok.connect(port).public_url
            print(f"Ngrok tunnel: {public_url} -> http://127.0.0.1:{port}")
            print("請把 LINE Developers 的 Webhook URL 設為:", public_url + "/callback")
        except Exception as e:
            print("ngrok 啟動失敗或未安裝：", e)

    # use_reloader=False 避免 debug 雙重啟動 ngrok
    app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=False)
