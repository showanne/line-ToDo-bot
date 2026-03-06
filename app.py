# app.py
import os
import re
from datetime import datetime
from flask import Flask, request, abort, jsonify
from dotenv import load_dotenv

# 引入 LINE Messaging API 相關模型與元件
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

# 處理 Webhook 解析器的相容性
try:
    from linebot.v3.webhook import WebhookParser
except Exception:
    from linebot.v3.webhooks import WebhookParser

# 載入 .env 環境變數
load_dotenv()

# 引入自定義的資料庫操作模組
import database as db

# 從環境變數讀取 LINE Channel 的存取憑證
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("請在 .env 設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")

# 初始化 Flask 應用程式與 LINE Webhook 解析器
app = Flask(__name__)
parser = WebhookParser(channel_secret=CHANNEL_SECRET)

# 初始化資料庫結構
db.init_db()

# ------------------------
# 輔助函式 (Helper Functions)
# ------------------------

def extract_tags(text):
    """
    從訊息字串中提取標籤（例如：#緊急 #生活）
    返回：標籤列表, 移除標籤後的原始文字
    """
    tags = re.findall(r'#([^\s#]+)', text)
    clean_text = re.sub(r'#[^\s#]+', '', text).strip()
    return tags, clean_text

def get_quick_reply(labels):
    """
    生成 LINE Quick Reply (快速回覆) 選項按鈕
    """
    if not labels: return None
    items = [QuickReplyItem(action=MessageAction(label=label, text=label)) for label in labels]
    return QuickReply(items=items)

# ------------------------
# Flex Message 生成邏輯
# ------------------------

def create_todo_flex_message(items, group_by_sub_category=False, offset=0, base_command="list", compact=False, parent_category=None):
    """
    生成待辦事項的 Flex Message 清單。
    遵循「3-9-1 法則」：
    - 3: 每張卡片最多顯示 3 個事項
    - 9: 每輪 Carousel 最多顯示 9 張資料卡片
    - 1: 第 10 張卡片固定為「下一頁」按鈕
    """
    if not items: return None
    
    # 1. 將資料庫項目按類別進行初步分組
    groups = {}
    for i in items:
        if group_by_sub_category:
            sub_cat_str = i[7]
            sub_cat_list = [s.strip() for s in sub_cat_str.split(",")] if sub_cat_str else ["未分類"]
            for sc in sub_cat_list:
                if sc not in groups: groups[sc] = []
                groups[sc].append(i)
        else:
            cat_name = str(i[6]) if i[6] else "未分類"
            if cat_name not in groups: groups[cat_name] = []
            groups[cat_name].append(i)

    # 2. 將分組資料拆解成「符合 Bubble 規格」的列表 (每 3 項一個 Bubble)
    bubble_specs = []
    for group_name, group_items in groups.items():
        # 按 ID 倒序排列（最新事項在前）
        sorted_items = sorted(group_items, key=lambda x: x[0], reverse=True)
        chunks = [sorted_items[x:x+3] for x in range(0, len(sorted_items), 3)]
        
        if compact:
            # 簡潔模式：每個分類僅顯示第一張卡片
            bubble_specs.append({
                "name": group_name, "items": chunks[0], 
                "show_more": len(sorted_items) > 3, "total_count": len(sorted_items)
            })
        else:
            # 完整模式：顯示所有拆分後的卡片，並標註序號（如：工作 (1/2)）
            for idx, chunk in enumerate(chunks):
                label = f"{group_name} ({idx+1}/{len(chunks)})" if len(chunks) > 1 else group_name
                bubble_specs.append({"name": label, "items": chunk, "show_more": False})

    # 3. 處理分頁 (9+1 規則)
    total_bubbles = len(bubble_specs)
    has_next = False
    next_offset = offset + 9
    
    # 決定本次要顯示哪些卡片
    display_specs = bubble_specs[offset:offset+9] if total_bubbles > offset + 10 else bubble_specs[offset:offset+10]
    if total_bubbles > offset + 10: has_next = True

    bubbles = []
    for spec in display_specs:
        contents = []
        for idx, item in enumerate(spec["items"]):
            item_id, title, _, is_done, place, _, _, sub_cats, tags = item
            
            # 建立單一事項的顯示方塊
            item_box = {"type": "box", "layout": "vertical", "spacing": "sm", "contents": [
                {"type": "box", "layout": "horizontal", "contents": [
                    {"type": "text", "text": f"#{item_id}", "size": "xs", "color": "#aaaaaa", "flex": 0},
                    {"type": "text", "text": title, "weight": "bold", "size": "md", "flex": 1, "margin": "md", "wrap": True}
                ]}
            ]}
            
            # 加入標籤與地點資訊
            details = []
            if tags: details.append({"type": "text", "text": "#" + str(tags).replace(", ", " #"), "size": "xs", "color": "#1db446", "wrap": True})
            info = f"子分類: {sub_cats or '無'}" if not group_by_sub_category else f"主分類: {item[6] or '無'}"
            if place: info += f" | 地點: {place}"
            details.append({"type": "text", "text": info, "size": "xxs", "color": "#999999", "wrap": True})
            item_box["contents"].append({"type": "box", "layout": "vertical", "margin": "sm", "contents": details})
            
            # 互動按鈕：完成與刪除
            btn_box = {"type": "box", "layout": "horizontal", "margin": "md", "spacing": "sm", "contents": []}
            if not is_done:
                btn_box["contents"].append({
                    "type": "box", "layout": "vertical", "backgroundColor": "#8D6E63", "cornerRadius": "sm", "paddingAll": "4px",
                    "action": {"type": "message", "label": "完成", "text": f"完成 {item_id}"},
                    "contents": [{"type": "text", "text": "完成", "color": "#ffffff", "size": "xs", "align": "center"}]
                })
            btn_box["contents"].append({
                "type": "box", "layout": "vertical", "backgroundColor": "#EEEEEE", "cornerRadius": "sm", "paddingAll": "4px",
                "action": {"type": "message", "label": "刪除", "text": f"刪除 {item_id}"},
                "contents": [{"type": "text", "text": "刪除", "color": "#616161", "size": "xs", "align": "center"}]
            })
            item_box["contents"].append(btn_box)
            
            contents.append(item_box)
            # 項目間的分隔線
            if idx < len(spec["items"]) - 1:
                contents.append({"type": "separator", "margin": "lg", "color": "#F5F5F5"})

        # 若為摘要模式且有隱藏項目，顯示「查看全部」連結
        if compact and spec.get("show_more"):
            target_cmd = f"list {spec['name']}" if not group_by_sub_category else f"list {parent_category}/{spec['name']}"
            contents.append({"type": "separator", "margin": "xl", "color": "#F5F5F5"})
            contents.append({
                "type": "button", "style": "link", "height": "sm", "color": "#8D6E63",
                "action": {"type": "message", "label": f"查看全部 ({spec['total_count']})", "text": target_cmd}
            })

        # 組裝成 Bubble
        bubbles.append({
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": "#E67E22",
                "contents": [{"type": "text", "text": spec["name"], "weight": "bold", "size": "xl", "color": "#ffffff", "align": "center"}]},
            "body": {"type": "box", "layout": "vertical", "contents": contents}
        })

    # 若還有剩餘頁面，加入下一頁按鈕
    if has_next:
        bubbles.append({"type": "bubble", "body": {"type": "box", "layout": "vertical", "justifyContent": "center", "spacing": "md", "contents": [
            {"type": "text", "text": "還有更多內容", "weight": "bold", "size": "md", "align": "center"},
            {"type": "button", "style": "primary", "color": "#E67E22", "margin": "xl",
                "action": {"type": "message", "label": "下一頁", "text": f"{base_command} @{next_offset}"}}]}})
    
    return {"type": "carousel", "contents": bubbles} if len(bubbles) > 1 else bubbles[0]

def create_category_management_flex(grouped_data, is_sub=False, offset=0, base_command="categories"):
    """
    生成分類管理的 Flex Message (包含摘要、更名、預填新增功能)。
    同樣遵循 3-9-1 法則以應對大量分類。
    """
    bubble_specs = []
    if is_sub:
        # 子分類模式：將同一主分類的子類按每 3 個一組拆分
        for main_cat, subs in grouped_data.items():
            chunks = [subs[x:x+3] for x in range(0, len(subs), 3)]
            for idx, chunk in enumerate(chunks):
                label = f"{main_cat} ({idx+1}/{len(chunks)})" if len(chunks) > 1 else main_cat
                bubble_specs.append({"type": "sub", "header": label, "main": main_cat, "items": chunk})
    else:
        # 主分類模式：每張卡片代表 1 個主分類
        for main_cat in grouped_data.keys():
            bubble_specs.append({"type": "main", "header": main_cat, "main": main_cat})

    # 分頁計算
    total_bubbles = len(bubble_specs)
    has_next = False
    next_offset = offset + 9
    display_specs = bubble_specs[offset:offset+9] if total_bubbles > offset + 10 else bubble_specs[offset:offset+10]
    if total_bubbles > offset + 10: has_next = True

    bubbles = []
    for spec in display_specs:
        contents = []
        if spec["type"] == "sub":
            # 子分類卡片內容 (清單式按鈕)
            for idx, sub in enumerate(spec["items"]):
                path = f"{spec['main']}/{sub}"
                row = {"type": "box", "layout": "horizontal", "spacing": "sm", "alignItems": "center", "contents": [
                    {"type": "text", "text": sub, "weight": "bold", "size": "sm", "color": "#424242", "flex": 4, 
                     "action": {"type": "message", "label": sub, "text": f"list {path}"}},
                    {"type": "box", "layout": "vertical", "backgroundColor": "#BDBDBD", "cornerRadius": "sm", "paddingAll": "4px", "flex": 2,
                     "action": {"type": "message", "label": "改名", "text": f"rename_sub {path} -> "},
                     "contents": [{"type": "text", "text": "改名", "color": "#ffffff", "size": "xxs", "align": "center"}]},
                    {"type": "box", "layout": "vertical", "backgroundColor": "#E67E22", "cornerRadius": "sm", "paddingAll": "4px", "flex": 2,
                     "action": {"type": "message", "label": "新增", "text": f"新增 {path}"},
                     "contents": [{"type": "text", "text": "新增", "color": "#ffffff", "size": "xxs", "align": "center"}]}
                ]}
                contents.append(row)
                if idx < len(spec["items"]) - 1: contents.append({"type": "separator", "margin": "sm", "color": "#F5F5F5"})
        else:
            # 主分類卡片內容 (大型管理按鈕)
            m = spec["main"]
            contents = [
                {"type": "box", "layout": "vertical", "backgroundColor": "#8D6E63", "cornerRadius": "sm", "paddingAll": "8px", "margin": "md",
                 "action": {"type": "message", "label": "摘要", "text": f"list {m}"},
                 "contents": [{"type": "text", "text": "查看清單摘要", "color": "#ffffff", "size": "sm", "align": "center"}]},
                {"type": "box", "layout": "vertical", "backgroundColor": "#BDBDBD", "cornerRadius": "sm", "paddingAll": "8px", "margin": "sm",
                 "action": {"type": "message", "label": "更名", "text": f"rename_cat {m} -> "},
                 "contents": [{"type": "text", "text": "重新命名類別", "color": "#ffffff", "size": "sm", "align": "center"}]},
                {"type": "box", "layout": "vertical", "backgroundColor": "#E67E22", "cornerRadius": "sm", "paddingAll": "8px", "margin": "sm",
                 "action": {"type": "message", "label": "新增", "text": f"新增 {m}"},
                 "contents": [{"type": "text", "text": "於此分類新增項目", "color": "#ffffff", "size": "sm", "align": "center"}]}
            ]

        bubbles.append({
            "type": "bubble",
            "header": {"type": "box", "layout": "vertical", "backgroundColor": "#EFEBE9", "contents": [
                {"type": "text", "text": spec["header"], "weight": "bold", "size": "lg", "color": "#424242", "align": "center"},
                {"type": "text", "text": "子分類列表" if spec["type"] == "sub" else "主分類管理", "size": "xs", "color": "#9E9E9E", "align": "center", "margin": "xs"}
            ]},
            "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": contents}
        })

    if has_next:
        bubbles.append({"type": "bubble", "body": {"type": "box", "layout": "vertical", "justifyContent": "center", "spacing": "md", "contents": [
            {"type": "text", "text": "更多分類", "weight": "bold", "size": "md", "align": "center"},
            {"type": "button", "style": "primary", "color": "#E67E22", "margin": "xl",
                "action": {"type": "message", "label": "下一頁", "text": f"{base_command} @{next_offset}"}}]}})
    
    return {"type": "carousel", "contents": bubbles} if len(bubbles) > 1 else bubbles[0]

# ------------------------
# 多步驟流程處理 (State Handling)
# ------------------------

def handle_stateful_message(user_id, state, text):
    """
    處理使用者正處於「新增中」或「編輯中」的對話狀態。
    """
    action = state.get("action"); t = text.strip()
    if t.lower() == "取消": db.clear_user_state(user_id); return "操作已取消。", None
    
    # 處理「逐步新增」流程
    if action == "add_item":
        stage = state.get("stage")
        if stage == "awaiting_category":
            state["data"] = {"category": t}; state["stage"] = "awaiting_sub_category"; db.set_user_state(user_id, state)
            return "請輸入子分類（多個請用逗號隔開）：", get_quick_reply(["取消"])
        elif stage == "awaiting_sub_category":
            state["data"]["sub_categories"] = [s.strip() for s in t.split(",") if s.strip()]; state["stage"] = "awaiting_title"; db.set_user_state(user_id, state)
            return "請輸入待辦事項名稱：", get_quick_reply(["取消"])
        elif stage == "awaiting_title":
            tags, clean_title = extract_tags(t); state["data"]["title"] = clean_title; state["data"]["tags"] = tags; state["stage"] = "awaiting_place"; db.set_user_state(user_id, state)
            return "請輸入地點（若無請輸入'無'）：", get_quick_reply(["無", "取消"])
        elif stage == "awaiting_place":
            place = t if t.lower() not in ["無", "none", "skip"] else None; data = state["data"]
            db.add_item(user_id, data["category"], data["sub_categories"], data["title"], tags=data["tags"], place=place)
            db.clear_user_state(user_id); return f"已新增：{data['title']} ({data['category']})", None
            
    # 處理「編輯」流程
    elif action == "edit_item":
        stage = state.get("stage"); item_id = state.get("item_id")
        if stage == "awaiting_field_choice":
            if t in ["1", "名稱"]:
                state["stage"] = "awaiting_new_value"; state["field"] = "title"; db.set_user_state(user_id, state)
                return "請輸入新的「名稱」：", get_quick_reply(["取消"])
            elif t in ["2", "地點"]:
                state["stage"] = "awaiting_new_value"; state["field"] = "place"; db.set_user_state(user_id, state)
                return "請輸入新的「地點」（若要清空請輸入'無'）：", get_quick_reply(["無", "取消"])
        elif stage == "awaiting_new_value":
            field = state.get("field"); value = t if not (field == 'place' and t.lower() in ['無', 'none']) else None
            if db.edit_item(user_id, item_id, field, value):
                db.clear_user_state(user_id); return f"待辦事項 [{item_id}] 已更新。", None
                
    # 處理「更名」流程
    elif action == "rename_cat":
        if db.rename_category(user_id, state.get("old_name"), t): db.clear_user_state(user_id); return f"更名成功：{t}", None
    elif action == "rename_sub":
        if db.rename_sub_category(user_id, state.get("category_name"), state.get("old_name"), t): db.clear_user_state(user_id); return f"更名成功：{t}", None

    return "操作失敗，請取消後重試。", None

# ------------------------
# 健康檢查端點 (Health Check)
# ------------------------

@app.get("/health")
def health():
    """
    提供給監測工具 (如 UptimeRobot) 的簡單端點，確認服務在線。
    """
    return jsonify({"status": "ok", "message": "Service is running"}), 200

# ------------------------
# LINE Webhook 主要入口
# ------------------------

@app.post("/callback")
def callback():
    signature = request.headers.get("X-Line-Signature", ""); body = request.get_data(as_text=True)
    try: events = parser.parse(body, signature)
    except: abort(400)
    
    for event in events:
        user_id = getattr(event.source, "user_id", None)
        if getattr(event, "type", None) == "message":
            msg = getattr(event, "message", None); text = getattr(msg, "text", None)
            reply_token = getattr(event, "reply_token", None); quick_reply = None; flex_contents = None; reply_text = ""
            
            if text:
                t = text.strip(); current_state = db.get_user_state(user_id)
                # 優先檢查是否處於流程狀態
                if current_state: 
                    reply_text, quick_reply = handle_stateful_message(user_id, current_state, t)
                elif "++" in t: # 快捷多筆新增語法
                    try:
                        main_p = t.split("++"); left_p = [p.strip() for p in main_p[0].split("+")]
                        cat = left_p[0]; subs = [s.strip() for s in left_p[1].split(",")]; items = [i.strip() for i in main_p[1].split(",")]; added = 0
                        for i_s in items:
                            if i_s: tags, clean_t = extract_tags(i_s); db.add_item(user_id, cat, subs, clean_t, tags=tags); added += 1
                        reply_text = f"已批次新增 {added} 項。"
                    except: reply_text = "格式錯誤。"
                elif "+" in t and len(t.split("+")) >= 3: # 快捷單筆新增語法
                    try:
                        parts = [p.strip() for p in t.split("+")]; cat = parts[0]; subs = [s.strip() for s in parts[1].split(",")]; tags, clean_t = extract_tags(parts[2])
                        db.add_item(user_id, cat, subs, clean_t, tags=tags); reply_text = f"已新增：{clean_t}"
                    except: reply_text = "格式錯誤。"
                else:
                    # 一般指令判斷
                    t_lower = t.lower()
                    if t_lower == "ping": reply_text = "pong"
                    elif t_lower.startswith("新增") or t_lower.startswith("add"):
                        parts = t.split(" ", 1); initial_state = {"action": "add_item", "stage": "awaiting_category", "data": {}}
                        if len(parts) > 1: # 支援預填分類 (例如：新增 工作/會議)
                            path = parts[1].strip()
                            if "/" in path:
                                cp = path.split("/", 1); initial_state["data"] = {"category": cp[0].strip(), "sub_categories": [cp[1].strip()]}; initial_state["stage"] = "awaiting_title"; reply_text = f"已預填：{cp[0]}/{cp[1]}，請輸入事項名稱："
                            else:
                                initial_state["data"] = {"category": path}; initial_state["stage"] = "awaiting_sub_category"; reply_text = f"已預填：{path}，請輸入子分類："
                        else: reply_text = "好的，請輸入主分類："
                        db.set_user_state(user_id, initial_state); quick_reply = get_quick_reply(["取消"])
                    elif t_lower.startswith("編輯 "):
                        try:
                            item_id = int(t.split(" ")[1]); item = db.get_item(user_id, item_id)
                            if item: db.set_user_state(user_id, {"action": "edit_item", "stage": "awaiting_field_choice", "item_id": item_id}); reply_text = f"正編輯 [{item_id}]：{item['title']}\n1. 名稱\n2. 地點"; quick_reply = get_quick_reply(["名稱", "地點", "取消"])
                            else: reply_text = "找不到項目。"
                        except: reply_text = "格式錯誤。"
                    elif t_lower.startswith("刪除 "):
                        try: ids = [int(i.strip()) for i in t.split(" ", 1)[1].split(",")]
                        except: ids = []; reply_text = "格式錯誤。"
                        if ids: count = db.delete_item(user_id, ids); reply_text = f"已刪除 {count} 項。"
                    elif t_lower.startswith("完成 "):
                        try: ids = [int(i.strip()) for i in t.split(" ", 1)[1].split(",")]
                        except: ids = []; reply_text = "格式錯誤。"
                        if ids: count = db.mark_item_as_done(user_id, ids); reply_text = f"已完成 {count} 項。"
                    elif t_lower in ["categories", "cat"] or t_lower.startswith("categories @"):
                        # 主分類管理與分頁處理
                        offset = 0; offset_match = re.search(r'@(\d+)$', t)
                        if offset_match: offset = int(offset_match.group(1))
                        cats = db.list_categories(user_id)
                        if cats: flex_contents = create_category_management_flex({c: [] for c in cats}, is_sub=False, offset=offset, base_command="categories"); reply_text = "主分類管理"
                        else: reply_text = "目前沒有分類。"
                    elif t_lower.startswith("sub_categories") or t_lower.startswith("subcat"):
                        # 子分類管理與分頁處理
                        offset = 0; offset_match = re.search(r'@(\d+)$', t); clean_t = t
                        if offset_match: offset = int(offset_match.group(1)); clean_t = t[:offset_match.start()].strip()
                        parts = clean_t.split(" ", 1); cat_f = parts[1].strip() if len(parts) > 1 else None; results = db.list_sub_categories(user_id, cat_f)
                        if results:
                            grouped = {}
                            for c, s in results:
                                if c not in grouped: grouped[c] = []
                                grouped[c].append(s)
                            flex_contents = create_category_management_flex(grouped, is_sub=True, offset=offset, base_command=clean_t); reply_text = f"子分類列表"
                        else: reply_text = "找不到子分類。"
                    elif t_lower.startswith("rename_cat "):
                        # 處理主分類更名
                        content = t[11:].strip()
                        if "->" in content:
                            p = content.split("->"); old_n = p[0].strip(); new_n = p[1].strip()
                            if old_n and new_n:
                                if db.rename_category(user_id, old_n, new_n): reply_text = f"成功：{old_n} -> {new_n}"
                                else: reply_text = "失敗。"
                            elif old_n: db.set_user_state(user_id, {"action": "rename_cat", "old_name": old_n}); reply_text = f"請輸入 [{old_n}] 的新名稱："; quick_reply = get_quick_reply(["取消"])
                    elif t_lower.startswith("list"):
                        # 處理待辦清單查詢與分頁
                        offset = 0; offset_match = re.search(r'@(\d+)$', t); clean_cmd = t
                        if offset_match: offset = int(offset_match.group(1)); clean_cmd = t[:offset_match.start()].strip()
                        arg = clean_cmd[4:].strip() if len(clean_cmd) > 4 else None; cat = None; sub = None
                        if arg:
                            if "/" in arg: p = arg.split("/", 1); cat = p[0].strip(); sub = p[1].strip()
                            else: cat = arg
                        items = db.list_items(user_id, cat, sub)
                        if items:
                            is_compact = True if not sub else False; flex_contents = create_todo_flex_message(items, bool(cat), offset, clean_cmd, is_compact, cat); reply_text = f"{cat or '您的'} 清單{'摘要' if is_compact else ''}"
                        else: reply_text = "沒有內容。"
                    elif t_lower == "help":
                        reply_text = "指令：\n- 新增 [分類/子類]\n- categories / sub_categories\n- list [分類/子類]\n- 編輯/刪除/完成 <ID>\n- rename_cat 舊->新\n- rename_sub 主/舊->新"; quick_reply = get_quick_reply(["新增", "categories", "list", "help"])
                    else: reply_text = f"收到：{text}"
            
            # 發送回應訊息 (Flex 或純文字)
            if reply_token:
                try:
                    with ApiClient(Configuration(access_token=CHANNEL_ACCESS_TOKEN)) as api_client:
                        messaging_api = MessagingApi(api_client)
                        messages = [FlexMessage(alt_text=reply_text, contents=FlexContainer.from_dict(flex_contents))] if flex_contents else [V3TextMessage(type="text", text=reply_text)]
                        if quick_reply: messages[0].quick_reply = quick_reply
                        messaging_api.reply_message(ReplyMessageRequest(reply_token=reply_token, messages=messages))
                except Exception as e: app.logger.error("Error: %s", e)
    return "OK", 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # 若非生產環境，啟動 ngrok 穿透
    if os.getenv("APP_ENV") != "production":
        try:
            from pyngrok import ngrok
            token = os.getenv("NGROK_AUTHTOKEN")
            if token: ngrok.set_auth_token(token)
            print(f"Ngrok: {ngrok.connect(port).public_url}")
        except: pass
    # 啟動 Flask Server
    app.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
