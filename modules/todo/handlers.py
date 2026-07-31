# modules/todo/handlers.py
import re
from linebot.v3.messaging.models import (
    ReplyMessageRequest,
    TextMessage as V3TextMessage,
    FlexMessage,
    FlexContainer
)
from core import database as core_db
from modules.base_module import BaseModule
from modules.todo import models as db
from modules.todo.api import todo_api
from modules.todo.flex_templates import (
    extract_metadata,
    get_quick_reply,
    create_todo_flex_message,
    create_item_detail_carousel,
    create_category_management_flex,
    create_simple_list_flex,
    create_help_flex_message
)

class TodoModule(BaseModule):
    @property
    def name(self) -> str:
        return "todo"

    @property
    def display_name(self) -> str:
        return "📝 待辦清單"

    def get_blueprint(self):
        return todo_api

    def handle_postback(self, messaging_api, event, user_id: str, postback_data: str, reply_token: str):
        # 處理幫助選單中觸發的指令預填填入
        pass

    def handle_message(self, messaging_api, event, user_id: str, text: str, reply_token: str):
        text = text.strip()
        state = core_db.get_user_state(user_id)

        # 1. 優先處理「狀態中」的對話
        if state:
            reply_text, quick_reply, flex_content = self._handle_stateful_message(user_id, state, text)
            self._reply(messaging_api, reply_token, reply_text, quick_reply, flex_content)
            return

        # 2. 解析多筆快捷新增指令
        if "++" in text:
            reply_text, quick_reply, flex_content = self._handle_batch_add(user_id, text)
            self._reply(messaging_api, reply_token, reply_text, quick_reply, flex_content)
            return

        # 3. 解析單筆快捷新增指令
        if "+" in text and not text.startswith("list"):
            reply_text, quick_reply, flex_content = self._handle_single_add(user_id, text)
            self._reply(messaging_api, reply_token, reply_text, quick_reply, flex_content)
            return

        # 4. 解析一般指令
        reply_text, quick_reply, flex_content = self._handle_command(user_id, text)
        self._reply(messaging_api, reply_token, reply_text, quick_reply, flex_content)

    def _reply(self, messaging_api, reply_token, reply_text=None, quick_reply=None, flex_content=None):
        messages = []
        if flex_content:
            messages.append(FlexMessage(altText="待辦事項通知", contents=FlexContainer.from_dict(flex_content), quickReply=quick_reply))
        elif reply_text:
            messages.append(V3TextMessage(text=reply_text, quickReply=quick_reply))

        if messages:
            messaging_api.reply_message(ReplyMessageRequest(replyToken=reply_token, messages=messages))

    def _handle_stateful_message(self, user_id, state, text):
        action = state.get("action"); t = text.strip()
        if t.lower() == "取消":
            core_db.clear_user_state(user_id)
            return "操作已取消。", None, None

        if action == "add_item":
            stage = state.get("stage")
            if stage == "awaiting_category":
                state["data"] = {"category": t}
                state["stage"] = "awaiting_sub_category"
                core_db.set_user_state(user_id, state)
                return "請輸入子分類（多個請用逗號隔開）：", get_quick_reply(["取消"]), None
            elif stage == "awaiting_sub_category":
                state["data"]["sub_categories"] = [s.strip() for s in t.split(",") if s.strip()]
                state["stage"] = "awaiting_title"
                core_db.set_user_state(user_id, state)
                return "請輸入事項內容 (可包含 #標籤 與 @地點)：", get_quick_reply(["取消"]), None
            elif stage == "awaiting_title":
                tags, place, clean_title = extract_metadata(t)
                data = state["data"]
                cat = data["category"]; subs = data.get("sub_categories", [])
                new_id = db.add_item(user_id, cat, subs, clean_title, tags=tags, place=place)
                core_db.clear_user_state(user_id)
                items = db.list_items(user_id, item_ids=[new_id])

                sub_path = f"{cat}/{subs[0]}" if subs else cat
                flex = create_item_detail_carousel(items, context_info={"type": "category", "val": sub_path}, is_new=True)

                sub_val = subs[0] if subs else ""
                qr_options = [
                    ("📜列出項目", f"list {cat}/{sub_val}" if sub_val else f"list {cat}"),
                    ("➕繼續新增", f"新增 {cat}/{sub_val}" if sub_val else f"新增 {cat}"),
                    ("📁主分類", "cat")
                ]
                return f"已新增：{clean_title}", get_quick_reply(qr_options), flex

        elif action == "edit_item":
            stage = state.get("stage"); item_id = state.get("item_id")
            if stage == "awaiting_field_choice":
                if t in ["1", "名稱"]:
                    state["stage"] = "awaiting_new_value"; state["field"] = "title"; core_db.set_user_state(user_id, state)
                    return "請輸入新的「名稱」：", get_quick_reply(["取消"]), None
                elif t in ["2", "地點"]:
                    state["stage"] = "awaiting_new_value"; state["field"] = "place"; core_db.set_user_state(user_id, state)
                    return "請輸入新的「地點」（若要清空請輸入'無'）：", get_quick_reply(["無", "取消"]), None
            elif stage == "awaiting_new_value":
                field = state.get("field"); value = t if not (field == 'place' and t.lower() in ['無', 'none']) else None
                if db.edit_item(user_id, item_id, field, value):
                    core_db.clear_user_state(user_id)
                    items = db.list_items(user_id, item_ids=[item_id])
                    cat = items[0][6] if items else "main"
                    flex = create_item_detail_carousel(items, context_info={"type": "category", "val": cat}, is_new=True)
                    return f"待辦事項 [{item_id}] 已更新。", None, flex

        elif action == "rename_cat":
            if db.rename_category(user_id, state.get("old_name"), t):
                core_db.clear_user_state(user_id)
                return f"更名成功：{t}", None, None
        elif action == "rename_sub":
            if db.rename_sub_category(user_id, state.get("category_name"), state.get("old_name"), t):
                core_db.clear_user_state(user_id)
                return f"更名成功：{t}", None, None

        return "對話狀態錯誤，已自動清理。", None, None

    def _handle_batch_add(self, user_id, text):
        parts = text.split("++")
        cat_part = parts[0].strip()
        items_part = parts[1].strip()

        cats = [c.strip() for c in cat_part.split("+") if c.strip()]
        if len(cats) < 2:
            return "格式錯誤。範例：追劇清單 + 言情 ++ 偷偷藏不住 @優酷, 難哄 @Netflix #必看", None, None

        category = cats[0]
        sub_categories = [s.strip() for s in cats[1].split(",") if s.strip()]

        raw_items = [i.strip() for i in items_part.split(",") if i.strip()]
        added_ids = []

        for item_str in raw_items:
            tags, place, title = extract_metadata(item_str)
            if title:
                item_id = db.add_item(user_id, category, sub_categories, title, tags=tags, place=place)
                added_ids.append(item_id)

        if added_ids:
            items = db.list_items(user_id, item_ids=added_ids)
            sub_path = f"{category}/{sub_categories[0]}" if sub_categories else category
            flex = create_item_detail_carousel(items, context_info={"type": "category", "val": sub_path}, is_new=True)

            sub_val = sub_categories[0] if sub_categories else ""
            qr_options = [
                ("📜列出項目", f"list {category}/{sub_val}" if sub_val else f"list {category}"),
                ("➕繼續新增", f"新增 {category}/{sub_val}" if sub_val else f"新增 {category}"),
                ("📁主分類", "cat")
            ]
            return f"成功批次新增 {len(added_ids)} 筆事項！", get_quick_reply(qr_options), flex
        else:
            return "未能新增任何事項，請檢查格式。", None, None

    def _handle_single_add(self, user_id, text):
        parts = [p.strip() for p in text.split("+") if p.strip()]
        if len(parts) >= 3:
            category = parts[0]
            sub_categories = [s.strip() for s in parts[1].split(",") if s.strip()]
            item_raw = parts[2]

            tags, place, title = extract_metadata(item_raw)
            item_id = db.add_item(user_id, category, sub_categories, title, tags=tags, place=place)

            items = db.list_items(user_id, item_ids=[item_id])
            sub_path = f"{category}/{sub_categories[0]}" if sub_categories else category
            flex = create_item_detail_carousel(items, context_info={"type": "category", "val": sub_path}, is_new=True)

            sub_val = sub_categories[0] if sub_categories else ""
            qr_options = [
                ("📜列出項目", f"list {category}/{sub_val}" if sub_val else f"list {category}"),
                ("➕繼續新增", f"新增 {category}/{sub_val}" if sub_val else f"新增 {category}"),
                ("📁主分類", "cat")
            ]
            return f"成功新增：{title}", get_quick_reply(qr_options), flex
        else:
            return "格式錯誤。範例：追劇清單 + 言情 + 劇名 #標籤 @地點", None, None

    def _handle_command(self, user_id, text):
        t = text.strip()

        if t.lower() in ["help", "幫助", "指令"]:
            return None, None, create_help_flex_message()

        if t.lower() == "ping":
            return "pong 🏓 待辦服務正常運行中", None, None

        if t.lower() == "contact":
            return "聯絡開發者：showanne.e@gmail.com", None, None

        if t.startswith("新增"):
            path = t[2:].strip()
            if path:
                parts = path.split("/")
                cat = parts[0].strip()
                sub = parts[1].strip() if len(parts) > 1 else ""
                state = {"action": "add_item", "stage": "awaiting_title", "data": {"category": cat, "sub_categories": [sub] if sub else []}}
                core_db.set_user_state(user_id, state)
                return f"已設定為 [{path}]，請輸入事項內容 (可包含 #標籤 與 @地點)：", get_quick_reply(["取消"]), None
            else:
                state = {"action": "add_item", "stage": "awaiting_category"}
                core_db.set_user_state(user_id, state)
                return "請輸入主分類名稱：", get_quick_reply(["取消"]), None

        if t.lower() in ["categories", "cat"] or t.lower().startswith("categories ") or t.lower().startswith("cat "):
            offset = 0
            if "@" in t:
                try: offset = int(t.split("@")[1].strip())
                except: pass
            grouped = db.list_categories(user_id)
            grouped_dict = {name: count for name, count in grouped}
            flex = create_category_management_flex(grouped_dict, is_sub=False, offset=offset, base_command="cat")
            return None, None, flex

        if t.lower() in ["sub_categories", "subcat"] or t.lower().startswith("sub_categories ") or t.lower().startswith("subcat "):
            offset = 0
            if "@" in t:
                try: offset = int(t.split("@")[1].strip())
                except: pass
            param = re.sub(r'@[0-9]+', '', t).replace("sub_categories", "").replace("subcat", "").strip()
            results = db.list_sub_categories(user_id, category_name=param if param else None)

            grouped = {}
            for cat, sub, count in results:
                if cat not in grouped: grouped[cat] = []
                grouped[cat].append((sub, count))

            flex = create_category_management_flex(grouped, is_sub=True, offset=offset, base_command=f"subcat {param}".strip())
            return None, None, flex

        if t.lower() in ["tags", "標籤"]:
            tags = db.list_tags(user_id)
            flex = create_simple_list_flex("🏷️ 標籤清單", tags, prefix="#", base_command="list", context_type="search")
            return None, None, flex

        if t.lower() in ["places", "地點"]:
            places = db.list_places(user_id)
            flex = create_simple_list_flex("📍 地點清單", places, prefix="@", base_command="list", context_type="search")
            return None, None, flex

        if t.startswith("完成 "):
            ids_str = t[3:].strip()
            ids = [int(i.strip()) for i in ids_str.split(",") if i.strip().isdigit()]
            if ids:
                count = db.mark_item_as_done(user_id, ids)
                items = db.list_items(user_id, item_ids=ids)
                flex = create_item_detail_carousel(items, is_new=False)
                return f"已將 {count} 個項目標記為完成。", None, flex

        if t.startswith("刪除 "):
            ids_str = t[3:].strip()
            ids = [int(i.strip()) for i in ids_str.split(",") if i.strip().isdigit()]
            if ids:
                items = db.list_items(user_id, item_ids=ids)
                count = db.delete_item(user_id, ids)
                flex = create_item_detail_carousel(items, is_deleted=True)
                return f"已將 {count} 個項目刪除。", None, flex

        if t.startswith("復原 "):
            ids_str = t[3:].strip()
            ids = [int(i.strip()) for i in ids_str.split(",") if i.strip().isdigit()]
            if ids:
                count = db.restore_item(user_id, ids)
                items = db.list_items(user_id, item_ids=ids)
                flex = create_item_detail_carousel(items, is_new=True)
                return f"已將 {count} 個項目復原。", None, flex

        if t.startswith("編輯 "):
            item_id_str = t[3:].strip()
            if item_id_str.isdigit():
                item_id = int(item_id_str)
                item = db.get_item(user_id, item_id)
                if item:
                    state = {"action": "edit_item", "stage": "awaiting_field_choice", "item_id": item_id}
                    core_db.set_user_state(user_id, state)
                    msg = f"正在編輯 [{item['title']}]\n地點：{item['place'] or '無'}\n\n請選擇要修改的欄位：\n1. 名稱\n2. 地點"
                    return msg, get_quick_reply(["1. 名稱", "2. 地點", "取消"]), None

        if t.startswith("rename_cat "):
            expr = t[11:].strip()
            if "->" in expr:
                old, new = [x.strip() for x in expr.split("->", 1)]
                if db.rename_category(user_id, old, new): return f"主分類更名成功：{old} -> {new}", None, None

        if t.startswith("rename_sub "):
            expr = t[11:].strip()
            if "->" in expr:
                path_part, new = [x.strip() for x in expr.split("->", 1)]
                if "/" in path_part:
                    cat, old = [x.strip() for x in path_part.split("/", 1)]
                    if db.rename_sub_category(user_id, cat, old, new): return f"子分類更名成功：{old} -> {new}", None, None

        if t.startswith("#"):
            tag_name = t[1:].strip()
            items = db.list_items(user_id, tag_name=tag_name)
            if items:
                flex = create_todo_flex_message(items, offset=0, base_command=f"list #{tag_name}", context_info={"type": "tag", "val": tag_name})
                return None, None, flex
            else:
                return f"找不到帶有標籤 #{tag_name} 的待辦事項。", None, None

        if t.startswith("@"):
            place_name = t[1:].strip()
            items = db.list_items(user_id, place=place_name)
            if items:
                flex = create_todo_flex_message(items, offset=0, base_command=f"list @{place_name}", context_info={"type": "place", "val": place_name})
                return None, None, flex
            else:
                return f"找不到地點在 @{place_name} 的待辦事項。", None, None

        if t.startswith("list") or t == "所有待辦":
            offset = 0
            if "@" in t:
                try: offset = int(t.split("@")[1].strip())
                except: pass
            param = re.sub(r'@[0-9]+', '', t).replace("list", "").strip()

            if not param:
                items = db.list_items(user_id)
                if items:
                    flex = create_todo_flex_message(items, group_by_sub_category=False, offset=offset, base_command="list", compact=True)
                    return None, None, flex
                else:
                    return "目前沒有任何待辦事項！", None, None

            if param.startswith("#"):
                tag_name = param[1:]
                items = db.list_items(user_id, tag_name=tag_name)
                flex = create_todo_flex_message(items, offset=offset, base_command=f"list #{tag_name}", context_info={"type": "tag", "val": tag_name})
                return None, None, flex
            elif param.startswith("@"):
                place_name = param[1:]
                items = db.list_items(user_id, place=place_name)
                flex = create_todo_flex_message(items, offset=offset, base_command=f"list @{place_name}", context_info={"type": "place", "val": place_name})
                return None, None, flex

            if "/" in param:
                cat_name, sub_cat_name = [p.strip() for p in param.split("/", 1)]
                items = db.list_items(user_id, category_name=cat_name, sub_category_name=sub_cat_name)
                if items:
                    flex = create_todo_flex_message(items, group_by_sub_category=False, offset=offset, base_command=f"list {param}", header_title=param, context_info={"type": "subcategory", "val": param})
                    return None, None, flex
                else:
                    return f"[{param}] 目前沒有未完成的事項。", None, None
            else:
                cat_name = param
                items = db.list_items(user_id, category_name=cat_name)
                if items:
                    flex = create_todo_flex_message(items, group_by_sub_category=True, offset=offset, base_command=f"list {cat_name}", compact=True, context_info={"type": "category", "val": cat_name})
                    return None, None, flex
                else:
                    return f"主分類 [{cat_name}] 目前沒有任何事項。", None, None

        # 如果都不是上述指令，提示使用說明
        return "無法識別指令，請輸入 'help' 或點選選單檢視幫助說明。", None, None
