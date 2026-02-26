# app.py
import os
import re
from datetime import datetime
from flask import Flask, request, abort, jsonify
from dotenv import load_dotenv

from linebot.v3.messaging import Configuration, ApiClient, MessagingApi
from linebot.v3.messaging.models import (
    ReplyMessageRequest,
    TextMessage as V3TextMessage,
    QuickReply,
    QuickReplyItem,
    MessageAction
)

try:
    from linebot.v3.webhook import WebhookParser
except Exception:
    from linebot.v3.webhooks import WebhookParser

from dotenv import load_dotenv
load_dotenv()

import database as db

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("請在 .env 設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

app = Flask(__name__)
parser = WebhookParser(channel_secret=CHANNEL_SECRET)

# Initialize the database
db.init_db()

# ------------------------
# Helper Functions
# ------------------------
def extract_tags(text):
    """Extracts tags starting with # and returns them as a list, and the cleaned text."""
    tags = re.findall(r'#([^\s#]+)', text)
    # Remove tags from the text to avoid them being part of titles/places
    clean_text = re.sub(r'#[^\s#]+', '', text).strip()
    return tags, clean_text

def get_quick_reply(labels):
    if not labels:
        return None
    items = [QuickReplyItem(action=MessageAction(label=label, text=label)) for label in labels]
    return QuickReply(items=items)

# ------------------------
# Flask + LINE Webhook
# ------------------------
user_states = {}

def handle_stateful_message(user_id, text):
    state = user_states[user_id]
    action = state.get("action")
    t = text.strip()

    if t.lower() == "取消":
        del user_states[user_id]
        return "操作已取消。", None

    # --- Add Item Flow ---
    if action == "add_item":
        stage = state.get("stage")
        if stage == "awaiting_category":
            state["data"]["category"] = t
            state["stage"] = "awaiting_sub_category"
            return "請輸入子分類（多個請用逗號隔開）：", get_quick_reply(["取消"])
        elif stage == "awaiting_sub_category":
            state["data"]["sub_categories"] = [s.strip() for s in t.split(",") if s.strip()]
            state["stage"] = "awaiting_title"
            return "請輸入待辦事項名稱：", get_quick_reply(["取消"])
        elif stage == "awaiting_title":
            tags, clean_title = extract_tags(t)
            state["data"]["title"] = clean_title
            state["data"]["tags"] = tags
            state["stage"] = "awaiting_place"
            return "請輸入地點（若無請輸入'無'）：", get_quick_reply(["無", "取消"])
        elif stage == "awaiting_place":
            place = t if t.lower() not in ["無", "none", "skip"] else None
            data = state["data"]
            db.add_item(user_id, data["category"], data["sub_categories"], data["title"], tags=data["tags"], place=place)
            del user_states[user_id]
            sub_cat_str = ", ".join(data["sub_categories"])
            tag_str = " #" + " #".join(data["tags"]) if data["tags"] else ""
            return f"已新增：{data['title']} ({data['category']}/{sub_cat_str}){tag_str}" + (f"，地點：{place}" if place else ""), None

    # --- Edit Item Flow ---
    elif action == "edit_item":
        stage = state.get("stage")
        item_id = state.get("item_id")

        if stage == "awaiting_field_choice":
            if t in ["1", "名稱"]:
                state["stage"] = "awaiting_new_value"
                state["field"] = "title"
                return "請輸入新的「名稱」：", get_quick_reply(["取消"])
            elif t in ["2", "地點"]:
                state["stage"] = "awaiting_new_value"
                state["field"] = "place"
                return "請輸入新的「地點」（若要清空請輸入'無'）：", get_quick_reply(["無", "取消"])
            else:
                return "無效的選項，請重新輸入 (1 或 2)，或輸入'取消'。", get_quick_reply(["名稱", "地點", "取消"])

        elif stage == "awaiting_new_value":
            field = state.get("field")
            value = t if not (field == 'place' and t.lower() in ['無', 'none']) else None

            if db.edit_item(user_id, item_id, field, value):
                del user_states[user_id]
                return f"待辦事項 [{item_id}] 已更新。", None
            else:
                del user_states[user_id] # Clear state even on failure
                return f"更新失敗，找不到項目 [{item_id}] 或欄位不正確。", None

    return "發生未知錯誤，請取消後重試。", None


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
            quick_reply = None

            if text is None:
                reply_text = "我目前只處理文字訊息，請傳文字給我。"
            else:
                t = text.strip()

                if user_id in user_states:
                    reply_text, quick_reply = handle_stateful_message(user_id, t)
                # 快捷指令判斷
                elif "++" in t:
                    parts = [p.strip() for p in t.split("++")]
                    if len(parts) == 2:
                        context_parts = [p.strip() for p in parts[0].split("+")]
                        if len(context_parts) >= 2:
                            category = context_parts[0]
                            sub_category_raw = context_parts[1]
                            place = None
                            if len(context_parts) >= 3:
                                place = context_parts[2]

                            # Sub categories can be a list separated by comma
                            sub_categories = [s.strip() for s in sub_category_raw.split(",") if s.strip()]

                            items_raw = [i.strip() for i in parts[1].split(",")]
                            added_count = 0
                            for item_str in items_raw:
                                if item_str:
                                    tags, clean_title = extract_tags(item_str)
                                    db.add_item(user_id, category, sub_categories, clean_title, tags=tags, place=place)
                                    added_count += 1
                            if added_count > 0:
                                sub_cat_str = ", ".join(sub_categories)
                                reply_text = f"已在 {category}/{sub_cat_str}"
                                if place:
                                    reply_text += f" (地點: {place})"
                                reply_text += f" 新增 {added_count} 個項目。"
                            else:
                                reply_text = "沒有可新增的項目。"
                        else:
                            reply_text = "快捷指令格式錯誤，範例：主分類 + 子分類1,子分類2 [+ 地點] ++ 項目1 #標籤, 項目2..."
                    else:
                        reply_text = "快捷指令格式錯誤，範例：主分類 + 子分類1,子分類2 [+ 地點] ++ 項目1 #標籤, 項目2..."
                elif "+" in t:
                    parts = [p.strip() for p in t.split("+")]
                    if len(parts) >= 3:
                        category = parts[0]
                        sub_category_raw = parts[1]
                        title_raw = parts[2]
                        place = None
                        if len(parts) >= 4:
                            place = parts[3]

                        sub_categories = [s.strip() for s in sub_category_raw.split(",") if s.strip()]
                        tags, clean_title = extract_tags(title_raw)

                        db.add_item(user_id, category, sub_categories, clean_title, tags=tags, done=0, place=place)
                        sub_cat_str = ", ".join(sub_categories)
                        tag_str = " #" + " #".join(tags) if tags else ""
                        reply_text = f"已新增：{clean_title}{tag_str} ({category}/{sub_cat_str})" + (f"，地點：{place}" if place else "")
                    else:
                        reply_text = "快捷指令格式錯誤，範例：主分類 + 子分類1,子分類2 + 名稱 #標籤 [+ 地點]"
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
                        quick_reply = get_quick_reply(["取消"])
                    elif t_lower.startswith("編輯 ") or t_lower.startswith("edit "):
                        try:
                            item_id_str = t.split(" ")[1]
                            item_id = int(item_id_str)
                            item = db.get_item(user_id, item_id)
                            if item:
                                user_states[user_id] = {
                                    "action": "edit_item",
                                    "stage": "awaiting_field_choice",
                                    "item_id": item_id
                                }
                                sub_cat_str = item['sub_category_names'] or '無'
                                tag_str = " #" + item['tag_names'] if item['tag_names'] else '無'
                                reply_text = (
                                    f"您正要編輯項目 [{item['id']}]：{item['title']}\n"
                                    f"分類：{item['category_name']}/{sub_cat_str}\n"
                                    f"標籤：{tag_str}\n"
                                    f"地點：{item['place'] or '未設定'}\n\n"
                                    "您想編輯哪個欄位？\n"
                                    "1. 名稱\n"
                                    "2. 地點\n\n"
                                    "請輸入選項（或輸入'取消'）"
                                )
                                quick_reply = get_quick_reply(["名稱", "地點", "取消"])
                            else:
                                reply_text = f"找不到待辦事項 [{item_id}]。"
                        except (IndexError, ValueError):
                            reply_text = "編輯指令格式錯誤，請使用 '編輯 <編號>'"
                    elif t_lower.startswith("刪除 ") or t_lower.startswith("del "):
                        try:
                            item_ids_str = t.split(" ", 1)[1]
                            item_ids = [int(i.strip()) for i in item_ids_str.split(",")]
                            deleted_count = db.delete_item(user_id, item_ids)
                            reply_text = f"已刪除 {deleted_count} 個項目。"
                        except (IndexError, ValueError):
                            reply_text = "刪除指令格式錯誤，請使用 '刪除 <編號1>,<編號2>...'"
                    elif t_lower.startswith("完成 ") or t_lower.startswith("done "):
                        try:
                            item_ids_str = t.split(" ", 1)[1]
                            item_ids = [int(i.strip()) for i in item_ids_str.split(",")]
                            updated_count = db.mark_item_as_done(user_id, item_ids)
                            reply_text = f"已將 {updated_count} 個項目標示為完成。"
                        except (IndexError, ValueError):
                            reply_text = "完成指令格式錯誤，請使用 '完成 <編號1>,<編號2>...'"
                    elif t_lower == "help":
                        reply_text = "指令：\n- 新增 (逐步新增)\n- 編輯 <編號>\n- 刪除 <編號1>,<編號2>...\n- 完成 <編號1>,<編號2>...\n- list (列出項目)\n- list 主分類/子分類\n- 新增 (快捷): 主分類 + 子1,子2 + 名稱 #標籤 [+ 地點]\n- 多筆新增: 主分類 + 子1,子2 [+ 地點] ++ 項目1 #標籤, 項目2..."
                        quick_reply = get_quick_reply(["新增", "list", "help"])
                    elif t_lower == "contact":
                        reply_text = "如有任何問題，歡迎透過以下方式聯繫我們：\n📧 Email: example@email.com\n🌐 Website: https://github.com/your-repo"
                    elif t_lower.startswith("echo "):
                        reply_text = t[5:]
                    elif t_lower.startswith("list"):
                        cmd_arg = t[4:].strip() if len(t) > 4 else None
                        category = None
                        sub_category = None

                        if cmd_arg:
                            if "/" in cmd_arg:
                                parts = cmd_arg.split("/", 1)
                                category = parts[0].strip()
                                sub_category = parts[1].strip()
                            else:
                                category = cmd_arg

                        items = db.list_items(user_id, category, sub_category)
                        if not items:
                            reply_text = "目前沒有任何清單。"
                        else:
                            lines = []
                            current_category = None
                            for i in items:
                                # i: (id, title, desc, done, place, completed_date, cat_name, sub_cats, tags)
                                category_name = i[6]
                                if category_name != current_category:
                                    lines.append(f"\n--- {category_name} ---")
                                    current_category = category_name

                                status = "✅" if i[3] else "📝"
                                sub_cats = i[7] or "無"
                                tags = " #" + i[8] if i[8] else ""
                                line = f"{status} [{i[0]}] {i[1]}{tags} ({sub_cats})"
                                if i[3]:
                                    completed_time = datetime.fromisoformat(i[5]).strftime('%Y-%m-%d %H:%M')
                                    line += f" - 完成於 {completed_time}"
                                lines.append(line)
                            reply_text = "\n".join(lines).strip()
                        quick_reply = get_quick_reply(["新增", "list", "help"])
                    else:
                        reply_text = f"收到：{text}"

            if reply_token:
                try:
                    with ApiClient(Configuration(access_token=CHANNEL_ACCESS_TOKEN)) as api_client:
                        messaging_api = MessagingApi(api_client)
                        messages = [V3TextMessage(type="text", text=reply_text)]
                        if quick_reply:
                            messages[0].quick_reply = quick_reply
                        req = ReplyMessageRequest(
                            reply_token=reply_token,
                            messages=messages
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
                            messages=[V3TextMessage(
                                type="text",
                                text="謝謝你加我為好友！輸入 help 查看指令。",
                                quick_reply=get_quick_reply(["新增", "list", "help"])
                            )]
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
            ngrok_authtoken = os.getenv("NGROK_AUThtoken") # Note: was NGROK_AUTHTOKEN in previous read, fixing case if needed but stick to .env
            ngrok_authtoken = os.getenv("NGROK_AUTHTOKEN")
            if ngrok_authtoken:
                ngrok.set_auth_token(ngrok_authtoken)
            public_url = ngrok.connect(port).public_url
            print(f"Ngrok tunnel: {public_url} -> http://127.0.0.1:{port}")
            print("請把 LINE Developers 的 Webhook URL 設為:", public_url + "/callback")
        except Exception as e:
            print("ngrok 啟動失敗或未安裝：", e)

    app.run(host="0.0.0.0", port=port, debug=debug_mode, use_reloader=False)
