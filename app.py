# app.py
import os
import sqlite3
from datetime import datetime
from flask import Flask, request, abort, jsonify
from dotenv import load_dotenv

from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.messaging.models import ReplyMessageRequest, TextMessage as V3TextMessage

try:
    from linebot.v3.webhook import WebhookParser
except Exception:
    from linebot.v3.webhooks import WebhookParser

load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
DB_FILE = "todo.db"

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("請在 .env 設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

app = Flask(__name__)
parser = WebhookParser(channel_secret=CHANNEL_SECRET)

# ------------------------
# Database
# ------------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 使用者、分類、子分類、清單
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            name TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS sub_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            sub_category_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            desc TEXT,
            place TEXT,
            done INTEGER DEFAULT 0,
            completed_date TEXT,
            FOREIGN KEY(category_id) REFERENCES categories(id),
            FOREIGN KEY(sub_category_id) REFERENCES sub_categories(id)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ------------------------
# DB Helper
# ------------------------
def get_category_id(user_id, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM categories WHERE user_id=? AND name=?", (user_id, name))
    row = c.fetchone()
    if row:
        cid = row[0]
    else:
        c.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (user_id, name))
        cid = c.lastrowid
        conn.commit()
    conn.close()
    return cid

def get_sub_category_id(category_id, name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id FROM sub_categories WHERE category_id=? AND name=?", (category_id, name))
    row = c.fetchone()
    if row:
        sid = row[0]
    else:
        c.execute("INSERT INTO sub_categories (category_id, name) VALUES (?, ?)", (category_id, name))
        sid = c.lastrowid
        conn.commit()
    conn.close()
    return sid

def add_item(user_id, category, sub_category, title, desc="", done=0, place=None):
    cid = get_category_id(user_id, category)
    sid = get_sub_category_id(cid, sub_category)
    completed_date = datetime.now().isoformat() if done else None
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO items (user_id, category_id, sub_category_id, title, desc, place, done, completed_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, cid, sid, title, desc, place, done, completed_date))
    conn.commit()
    conn.close()

def delete_item(user_id, item_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 確保項目屬於該使用者
    c.execute("SELECT id FROM items WHERE id=? AND user_id=?", (item_id, user_id))
    item = c.fetchone()
    if item:
        c.execute("DELETE FROM items WHERE id=?", (item_id,))
        conn.commit()
        conn.close()
        return True
    else:
        conn.close()
        return False

def list_items(user_id, category=None, limit=5):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = """
        SELECT i.id, i.title, i.desc, i.done, i.place, i.completed_date, sc.name
        FROM items i
        JOIN categories c ON i.category_id = c.id
        JOIN sub_categories sc ON i.sub_category_id = sc.id
        WHERE i.user_id=?
    """
    params = [user_id]
    if category:
        query += " AND c.name=?"
        params.append(category)
    query += " ORDER BY i.id DESC LIMIT ?"
    params.append(limit)
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    return rows

# ------------------------
# Flask + LINE Webhook
# ------------------------
user_states = {}

def handle_step_by_step_add(user_id, text):
    state = user_states[user_id]
    stage = state.get("stage")
    t = text.strip()

    if t == "取消":
        del user_states[user_id]
        return "已取消新增操作。"

    if stage == "awaiting_category":
        state["data"]["category"] = t
        state["stage"] = "awaiting_sub_category"
        return "請輸入子分類："
    elif stage == "awaiting_sub_category":
        state["data"]["sub_category"] = t
        state["stage"] = "awaiting_title"
        return "請輸入待辦事項名稱："
    elif stage == "awaiting_title":
        state["data"]["title"] = t
        state["stage"] = "awaiting_place"
        return "請輸入地點（若無請輸入'無'）："
    elif stage == "awaiting_place":
        place = t if t not in ["無", "none", "skip"] else None
        data = state["data"]
        add_item(user_id, data["category"], data["sub_category"], data["title"], place=place)
        del user_states[user_id]
        return f"已新增：{data['title']} ({data['category']}/{data['sub_category']})" + (f"，地點：{place}" if place else "")
    return "發生未知錯誤，請取消後重試。"


@app.get("/health")
def health():
    return jsonify({"status": "ok"})

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
        user_id = getattr(event.source, "user_id", None)

        if ev_type == "message":
            msg = getattr(event, "message", None)
            text = getattr(msg, "text", None) if msg else None
            reply_token = getattr(event, "reply_token", None)

            if text is None:
                reply_text = "我目前只處理文字訊息，請傳文字給我。"
            else:
                t = text.strip()

                if user_id in user_states:
                    reply_text = handle_step_by_step_add(user_id, t)
                # 快捷指令判斷
                elif "+" in t:
                    parts = [p.strip() for p in t.split("+")]
                    if len(parts) >= 3:
                        category = parts[0]
                        sub_category = parts[1]
                        title = parts[2]
                        place = None
                        if len(parts) >= 4:
                            place = parts[3]
                        
                        add_item(user_id, category, sub_category, title, done=0, place=place)
                        reply_text = f"已新增：{title} ({category}/{sub_category})" + (f"，地點：{place}" if place else "")
                    else:
                        reply_text = "快捷指令格式錯誤，範例：主分類 + 子分類 + 名稱 [+ 地點]"
                else:
                    t_lower = t.lower()
                    if t_lower == "ping":
                        reply_text = "pong"
                    elif t_lower in ["新增", "add"]:
                        user_states[user_id] = {
                            "action": "add_item",
                            "stage": "awaiting_category",
                            "data": {}
                        }
                        reply_text = "好的，我們來新增一個待辦事項。請輸入主分類（或輸入'取消'）："
                    elif t_lower.startswith("刪除 ") or t_lower.startswith("del "):
                        try:
                            item_id_str = t.split(" ")[1]
                            item_id = int(item_id_str)
                            if delete_item(user_id, item_id):
                                reply_text = f"已刪除待辦事項 [{item_id}]。"
                            else:
                                reply_text = f"找不到待辦事項 [{item_id}]，或你沒有權限刪除它。"
                        except (IndexError, ValueError):
                            reply_text = "刪除指令格式錯誤，請使用 '刪除 <編號>'"
                    elif t_lower == "help":
                        reply_text = "指令：\n- 新增 (逐步新增)\n- 刪除 <編號>\n- list (列出項目)\n- 快捷指令: 主分類 + 子分類 + 名稱 [+ 地點]"
                    elif t_lower.startswith("echo "):
                        reply_text = t[5:]
                    elif t_lower.startswith("list"):
                        category = t[4:].strip() if len(t) > 4 else None
                        items = list_items(user_id, category)
                        if not items:
                            reply_text = "目前沒有任何清單。"
                        else:
                            lines = []
                            for i in items:
                                # i[0] is id, i[1] is title, i[6] is sub_category.name
                                lines.append(f"[{i[0]}] {i[1]} ({i[6]})" + (f" - 完成於 {i[5]}" if i[3] else ""))
                            reply_text = "\n".join(lines)
                    else:
                        reply_text = f"收到：{text}"

            if reply_token:
                try:
                    with ApiClient(Configuration(access_token=CHANNEL_ACCESS_TOKEN)) as api_client:
                        messaging_api = MessagingApi(api_client)
                        req = ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[V3TextMessage(type="text", text=reply_text)]
                        )
                        messaging_api.reply_message(req)
                except Exception as e:
                    app.logger.error("Failed to reply message: %s", e)

        elif ev_type == "follow":
            reply_token = getattr(event, "reply_token", None)
            if reply_token:
                try:
                    with ApiClient(Configuration(access_token=CHANNEL_ACCESS_TOKEN)) as api_client:
                        messaging_api = MessagingApi(api_client)
                        req = ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=[V3TextMessage(type="text", text="謝謝你加我為好友！輸入 help 查看指令。")]
                        )
                        messaging_api.reply_message(req)
                except Exception as e:
                    app.logger.error("Failed to reply follow event: %s", e)
        else:
            app.logger.debug("Unhandled event type: %s", ev_type)

    return "OK", 200

# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    debug_mode = True
    port = int(os.getenv("PORT", 5000))
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

    app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=False)
