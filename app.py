# app.py
import os
from flask import Flask, request, abort, jsonify, send_file
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

# 引入 LINE SDK 元件
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
try:
    from linebot.v3.webhook import WebhookParser
except Exception:
    from linebot.v3.webhooks import WebhookParser

# 引入 Core 與 Module
from core.config import CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET
from core.database import init_db
from core.scheduler import start_scheduler
from core.router import MessageRouter
from modules.todo.api import todo_api
from modules.investment.api import investment_api

# 1. 初始化 Flask 應用與數據庫
app = Flask(__name__)
parser = WebhookParser(channel_secret=CHANNEL_SECRET)

init_db()
start_scheduler()

# 2. 註冊子模組與 Blueprint
app.register_blueprint(todo_api)
app.register_blueprint(investment_api)

# 3. 初始化訊息分發路由器 (Door)
router = MessageRouter()

# ------------------------
# 平台路由與 API
# ------------------------

@app.get("/health")
def health():
    """提供監測工具的健康檢查端點"""
    return jsonify({"status": "ok", "message": "Life Assistant Platform is running"}), 200

@app.get("/dashboard")
def dashboard():
    """提供視覺化看板網頁"""
    return send_file("dashboard.html")

# ------------------------
# LINE Webhook 入口 (The Door)
# ------------------------

@app.post("/callback")
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    try:
        events = parser.parse(body, signature)
    except Exception:
        abort(400)

    with ApiClient(Configuration(access_token=CHANNEL_ACCESS_TOKEN)) as api_client:
        messaging_api = MessagingApi(api_client)

        for event in events:
            user_id = getattr(event.source, "user_id", None)
            event_type = getattr(event, "type", None)
            reply_token = getattr(event, "reply_token", None)

            if not user_id or not reply_token:
                continue

            # 文字訊息處理
            if event_type == "message":
                msg = getattr(event, "message", None)
                text = getattr(msg, "text", None)
                if text:
                    router.dispatch_message(messaging_api, event, user_id, text, reply_token)

            # Postback 事件處理
            elif event_type == "postback":
                postback_data = getattr(getattr(event, "postback", None), "data", "")
                router.dispatch_postback(messaging_api, event, user_id, postback_data, reply_token)

    return "OK", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    if os.getenv("APP_ENV") != "production":
        try:
            from pyngrok import ngrok
            token = os.getenv("NGROK_AUTHTOKEN")
            if token:
                ngrok.set_auth_token(token)
            print(f"Ngrok: {ngrok.connect(port).public_url}")
        except Exception as e:
            print(f"Ngrok start skipped: {e}")

    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
