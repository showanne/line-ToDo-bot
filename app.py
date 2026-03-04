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
    MessageAction,
    FlexMessage,
    FlexContainer
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
# 輔助函式 (Helper Functions)
# ------------------------
def extract_tags(text):
    """
    從字串中提取以 # 開頭的標籤，並返回標籤列表與移除標籤後的乾淨文字。
    範例: "買牛奶 #生活 #急件" -> (['生活', '急件'], "買牛奶")
    """
    tags = re.findall(r'#([^\s#]+)', text)
    # 移除文字中的標籤，避免標籤被當作標題或地點的一部分
    clean_text = re.sub(r'#[^\s#]+', '', text).strip()
    return tags, clean_text

def get_quick_reply(labels):
    """
    根據提供的標籤列表生成 LINE Quick Reply (快速回覆) 選項。
    """
    if not labels:
        return None
    items = [QuickReplyItem(action=MessageAction(label=label, text=label)) for label in labels]
    return QuickReply(items=items)

def create_todo_flex_message(items, group_by_sub_category=False, offset=0, base_command="list"):
    """
    根據資料庫項目生成 LINE Flex Message。
    offset: 起始分類的索引。
    base_command: 用於分頁按鈕的基礎指令字串。
    """
    if not items:
        return None

    # 資料分組邏輯
    groups = {}
    for i in items:
        if group_by_sub_category:
            sub_cat_str = i[7]
            sub_cat_list = [s.strip() for s in sub_cat_str.split(",")] if sub_cat_str else ["未分類"]
            for sc in sub_cat_list:
                if sc not in groups:
                    groups[sc] = []
                groups[sc].append(i)
        else:
            cat_name = str(i[6]) if i[6] else "未分類"
            if cat_name not in groups:
                groups[cat_name] = []
            groups[cat_name].append(i)

    all_groups = list(groups.items())
    total_groups = len(all_groups)

    # 分頁判斷 (LINE 限制 10 個 Bubble)
    has_next = False
    next_offset = offset + 9
    if total_groups > offset + 10:
        # 如果剩餘數量大於 10，顯示前 9 個 + 1 個「下一頁」
        display_groups = all_groups[offset:offset+9]
        has_next = True
    else:
        # 如果剩餘數量 <= 10，直接全部顯示
        display_groups = all_groups[offset:offset+10]

    bubbles = []
    for group_name, group_items in display_groups:
        contents = []
        display_items = group_items[:15]

        for idx, item in enumerate(display_items):
            item_id = item[0]
            title = str(item[1]) if item[1] else "無標題"
            is_done = bool(item[3])
            place = item[4]
            sub_cats = item[7]
            tags = item[8]

            item_box = {
                "type": "box", "layout": "vertical", "spacing": "sm",
                "contents": [
                    {
                        "type": "box", "layout": "horizontal",
                        "contents": [
                            {"type": "text", "text": f"#{item_id}", "size": "xs", "color": "#aaaaaa", "flex": 0},
                            {"type": "text", "text": title, "weight": "bold", "size": "md", "flex": 1, "margin": "md", "wrap": True}
                        ]
                    }
                ]
            }

            details = []
            if tags:
                tag_str = "#" + str(tags).replace(", ", " #")
                details.append({"type": "text", "text": tag_str, "size": "xs", "color": "#1db446", "wrap": True})

            if not group_by_sub_category:
                info = f"子分類: {sub_cats or '無'}"
            else:
                info = f"主分類: {item[6] or '無'}"

            if place:
                info += f" | 地點: {place}"
            details.append({"type": "text", "text": info, "size": "xxs", "color": "#999999", "wrap": True})
            item_box["contents"].append({"type": "box", "layout": "vertical", "margin": "sm", "contents": details})

            buttons = []
            if not is_done:
                buttons.append({
                    "type": "button", "style": "primary", "height": "sm", "color": "#00b900",
                    "action": {"type": "message", "label": "完成", "text": f"完成 {item_id}"}
                })
            buttons.append({
                "type": "button", "style": "secondary", "height": "sm",
                "action": {"type": "message", "label": "刪除", "text": f"刪除 {item_id}"}
            })
            item_box["contents"].append({"type": "box", "layout": "horizontal", "margin": "md", "spacing": "sm", "contents": buttons})
            contents.append(item_box)
            if idx < len(display_items) - 1:
                contents.append({"type": "separator", "margin": "lg"})

        bubbles.append({
            "type": "bubble",
            "header": {
                "type": "box", "layout": "vertical", "backgroundColor": "#464a5c",
                "contents": [{"type": "text", "text": group_name, "weight": "bold", "size": "xl", "color": "#ffffff"}]
            },
            "body": {"type": "box", "layout": "vertical", "contents": contents}
        })

    # 插入「下一頁」Bubble
    if has_next:
        next_range = f"{next_offset + 1} ~ {min(next_offset + 9, total_groups)}"
        bubbles.append({
            "type": "bubble",
            "body": {
                "type": "box", "layout": "vertical", "justifyContent": "center", "spacing": "md", "contents": [
                    {"type": "text", "text": "還有更多分類", "weight": "bold", "size": "md", "align": "center"},
                    {"type": "text", "text": f"第 {next_range} 個分類", "size": "xs", "color": "#aaaaaa", "align": "center"},
                    {
                        "type": "button", "style": "primary", "color": "#464a5c", "margin": "xl",
                        "action": {
                            "type": "message", "label": "下一頁",
                            "text": f"{base_command} @{next_offset}"
                        }
                    }
                ]
            }
        })

    if len(bubbles) == 1:
        return bubbles[0]
    else:
        return {"type": "carousel", "contents": bubbles}

# ------------------------
# 狀態管理與多階層對話處理 (Persistent State Handling)
# ------------------------

def handle_stateful_message(user_id, state, text):
    """
    處理需要多步驟輸入的指令（如：逐步新增、編輯項目）。
    state: 傳入的目前狀態字典。
    """
    action = state.get("action")
    t = text.strip()

    # 任何時候輸入「取消」皆可中止流程
    if t.lower() == "取消":
        db.clear_user_state(user_id)
        return "操作已取消。", None

    # --- 逐步新增流程 (Add Item Flow) ---
    if action == "add_item":
        stage = state.get("stage")
        if stage == "awaiting_category":
            state["data"] = {"category": t}
            state["stage"] = "awaiting_sub_category"
            db.set_user_state(user_id, state)
            return "請輸入子分類（多個請用逗號隔開）：", get_quick_reply(["取消"])
        elif stage == "awaiting_sub_category":
            state["data"]["sub_categories"] = [s.strip() for s in t.split(",") if s.strip()]
            state["stage"] = "awaiting_title"
            db.set_user_state(user_id, state)
            return "請輸入待辦事項名稱：", get_quick_reply(["取消"])
        elif stage == "awaiting_title":
            tags, clean_title = extract_tags(t)
            state["data"]["title"] = clean_title
            state["data"]["tags"] = tags
            state["stage"] = "awaiting_place"
            db.set_user_state(user_id, state)
            return "請輸入地點（若無請輸入'無'）：", get_quick_reply(["無", "取消"])
        elif stage == "awaiting_place":
            place = t if t.lower() not in ["無", "none", "skip"] else None
            data = state["data"]
            db.add_item(user_id, data["category"], data["sub_categories"], data["title"], tags=data["tags"], place=place)
            db.clear_user_state(user_id)
            sub_cat_str = ", ".join(data["sub_categories"])
            tag_str = " #" + " #".join(data["tags"]) if data["tags"] else ""
            return f"已新增：{data['title']} ({data['category']}/{sub_cat_str}){tag_str}" + (f"，地點：{place}" if place else ""), None

    # --- 編輯項目流程 (Edit Item Flow) ---
    elif action == "edit_item":
        stage = state.get("stage")
        item_id = state.get("item_id")

        if stage == "awaiting_field_choice":
            if t in ["1", "名稱"]:
                state["stage"] = "awaiting_new_value"
                state["field"] = "title"
                db.set_user_state(user_id, state)
                return "請輸入新的「名稱」：", get_quick_reply(["取消"])
            elif t in ["2", "地點"]:
                state["stage"] = "awaiting_new_value"
                state["field"] = "place"
                db.set_user_state(user_id, state)
                return "請輸入新的「地點」（若要清空請輸入'無'）：", get_quick_reply(["無", "取消"])
            else:
                return "無效的選項，請重新輸入 (1 或 2)，或輸入'取消'。", get_quick_reply(["名稱", "地點", "取消"])

        elif stage == "awaiting_new_value":
            field = state.get("field")
            value = t if not (field == 'place' and t.lower() in ['無', 'none']) else None
            if db.edit_item(user_id, item_id, field, value):
                db.clear_user_state(user_id)
                return f"待辦事項 [{item_id}] 已更新。", None
            else:
                db.clear_user_state(user_id)
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
            flex_contents = None

            if text is None:
                reply_text = "我目前只處理文字訊息，請傳文字給我。"
            else:
                t = text.strip()
                # 從資料庫獲取使用者目前的狀態
                current_state = db.get_user_state(user_id)

                if current_state:
                    reply_text, quick_reply = handle_stateful_message(user_id, current_state, t)

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
                                reply_text = f"已在 {category}/{sub_cat_str}" + (f" (地點: {place})" if place else "") + f" 新增 {added_count} 個項目。"
                            else:
                                reply_text = "沒有可新增的項目。"
                        else:
                            reply_text = "快捷指令格式錯誤。"
                    else:
                        reply_text = "快捷指令格式錯誤。"

                elif "+" in t:
                    parts = [p.strip() for p in t.split("+")]
                    if len(parts) >= 3:
                        category = parts[0]
                        sub_category_raw = parts[1]
                        title_raw = parts[2]
                        place = parts[3] if len(parts) >= 4 else None
                        sub_categories = [s.strip() for s in sub_category_raw.split(",") if s.strip()]
                        tags, clean_title = extract_tags(title_raw)
                        db.add_item(user_id, category, sub_categories, clean_title, tags=tags, place=place)
                        sub_cat_str = ", ".join(sub_categories)
                        tag_str = " #" + " #".join(tags) if tags else ""
                        reply_text = f"已新增：{clean_title}{tag_str} ({category}/{sub_cat_str})" + (f"，地點：{place}" if place else "")
                    else:
                        reply_text = "快捷指令格式錯誤。"

                else:
                    t_lower = t.lower()
                    if t_lower == "ping":
                        reply_text = "pong"
                    elif t_lower in ["新增", "add"]:
                        initial_state = {"action": "add_item", "stage": "awaiting_category", "data": {}}
                        db.set_user_state(user_id, initial_state)
                        reply_text = "好的，我們來新增一個待辦事項。請輸入主分類（或輸入'取消'）："
                        quick_reply = get_quick_reply(["取消"])
                    elif t_lower.startswith("編輯 ") or t_lower.startswith("edit "):
                        try:
                            item_id = int(t.split(" ")[1])
                            item = db.get_item(user_id, item_id)
                            if item:
                                initial_state = {"action": "edit_item", "stage": "awaiting_field_choice", "item_id": item_id}
                                db.set_user_state(user_id, initial_state)
                                reply_text = f"您正要編輯 [{item['id']}]：{item['title']}\n1. 名稱\n2. 地點\n請選擇編號（或輸入'取消'）"
                                quick_reply = get_quick_reply(["名稱", "地點", "取消"])
                            else:
                                reply_text = f"找不到待辦事項 [{item_id}]。"
                        except (IndexError, ValueError):
                            reply_text = "編輯指令格式錯誤。"
                    elif t_lower.startswith("刪除 ") or t_lower.startswith("del "):
                        try:
                            item_ids = [int(i.strip()) for i in t.split(" ", 1)[1].split(",")]
                            count = db.delete_item(user_id, item_ids)
                            reply_text = f"已刪除 {count} 個項目。"
                        except (IndexError, ValueError):
                            reply_text = "刪除指令格式錯誤。"
                    elif t_lower.startswith("完成 ") or t_lower.startswith("done "):
                        try:
                            item_ids = [int(i.strip()) for i in t.split(" ", 1)[1].split(",")]
                            count = db.mark_item_as_done(user_id, item_ids)
                            reply_text = f"已將 {count} 個項目標示為完成。"
                        except (IndexError, ValueError):
                            reply_text = "完成指令格式錯誤。"
                    elif t_lower == "help":
                        reply_text = "指令：\n- 新增\n- 編輯 <編號>\n- 刪除 <編號>\n- 完成 <編號>\n- list (列出項目)\n- list 主分類/子分類"
                        quick_reply = get_quick_reply(["新增", "list", "help"])
                    elif t_lower.startswith("list"):
                        offset = 0
                        offset_match = re.search(r'@(\d+)$', t)
                        clean_cmd = t
                        if offset_match:
                            offset = int(offset_match.group(1))
                            clean_cmd = t[:offset_match.start()].strip()
                        cmd_arg = clean_cmd[4:].strip() if len(clean_cmd) > 4 else None
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
                            should_group_by_sub = True if category else False
                            flex_contents = create_todo_flex_message(items, group_by_sub_category=should_group_by_sub, offset=offset, base_command=clean_cmd)
                            reply_text = f"{category or '您的待辦'} 清單"
                        quick_reply = get_quick_reply(["新增", "list", "help"])
                    else:
                        reply_text = f"收到：{text}"

            if reply_token:
                try:
                    with ApiClient(Configuration(access_token=CHANNEL_ACCESS_TOKEN)) as api_client:
                        messaging_api = MessagingApi(api_client)
                        if flex_contents:
                            messages = [FlexMessage(alt_text=reply_text, contents=FlexContainer.from_dict(flex_contents))]
                        else:
                            messages = [V3TextMessage(type="text", text=reply_text)]
                        if quick_reply:
                            messages[0].quick_reply = quick_reply
                        req = ReplyMessageRequest(reply_token=reply_token, messages=messages)
                        messaging_api.reply_message(req)
                except Exception as e:
                    app.logger.error("Failed to reply message: %s", e)

        elif ev_type == "follow":
            reply_token = getattr(event, "reply_token", None)
            if reply_token:
                try:
                    with ApiClient(Configuration(access_token=CHANNEL_ACCESS_TOKEN)) as api_client:
                        messaging_api = MessagingApi(api_client)
                        req = ReplyMessageRequest(reply_token=reply_token, messages=[V3TextMessage(type="text", text="謝謝你加我為好友！", quick_reply=get_quick_reply(["新增", "list", "help"]))])
                        messaging_api.reply_message(req)
                except Exception as e:
                    app.logger.error("Failed to reply follow: %s", e)

    return "OK", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    if os.getenv("APP_ENV") != "production":
        try:
            from pyngrok import ngrok
            ngrok_authtoken = os.getenv("NGROK_AUTHTOKEN")
            if ngrok_authtoken:
                ngrok.set_auth_token(ngrok_authtoken)
            public_url = ngrok.connect(port).public_url
            print(f"Ngrok tunnel: {public_url} -> http://127.0.0.1:{port}")
        except Exception as e:
            print("ngrok 啟動失敗：", e)
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
