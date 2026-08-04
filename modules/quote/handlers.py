from linebot.v3.messaging.models import (
    ReplyMessageRequest,
    TextMessage as V3TextMessage,
    FlexMessage,
    FlexContainer,
)
from core import database as core_db
from modules.base_module import BaseModule
from modules.quote import models as db
from modules.quote.api import quote_api
from modules.quote.flex_templates import build_quote_help_flex, build_quote_success_flex, build_quote_flex_message


class QuoteModule(BaseModule):
    @property
    def name(self) -> str:
        return "quote"

    @property
    def display_name(self) -> str:
        return "💬 佳句記錄"

    def get_blueprint(self):
        return quote_api

    def handle_postback(self, messaging_api, event, user_id: str, postback_data: str, reply_token: str):
        if postback_data.startswith("delete_quote:"):
            try:
                quote_id = int(postback_data.split(":", 1)[1])
                if db.delete_quote(user_id, quote_id):
                    self._reply(messaging_api, reply_token, f"已刪除佳句 #{quote_id}。")
                else:
                    self._reply(messaging_api, reply_token, f"找不到該佳句 #{quote_id}。")
            except Exception:
                self._reply(messaging_api, reply_token, "刪除失敗。")
            return

        if postback_data.startswith("edit_quote:"):
            try:
                quote_id = int(postback_data.split(":", 1)[1])
                quote = db.get_quote(user_id, quote_id)
                if not quote:
                    self._reply(messaging_api, reply_token, f"找不到該佳句 #{quote_id}。")
                    return
                state = {
                    "module": "quote",
                    "action": "edit_quote",
                    "quote_id": quote_id,
                    "stage": "awaiting_content",
                }
                core_db.set_user_state(user_id, state)
                self._reply(messaging_api, reply_token, "請輸入新的佳句內容：")
            except Exception:
                self._reply(messaging_api, reply_token, "進入編輯模式失敗。")

    def handle_message(self, messaging_api, event, user_id: str, text: str, reply_token: str):
        text = text.strip()
        state = core_db.get_user_state(user_id)

        if state and state.get("module") == "quote":
            reply_text, quick_reply, flex_content = self._handle_stateful_message(user_id, state, text)
            self._reply_with_flex(messaging_api, reply_token, reply_text, quick_reply, flex_content)
            return

        t_lower = text.lower()

        if t_lower in ["help", "幫助", "說明", "指令"]:
            flex = build_quote_help_flex()
            self._reply_with_flex(messaging_api, reply_token, None, None, flex)
            return

        if t_lower in ["list", "列出佳句", "quotes", "佳句列表"]:
            quotes = db.list_quotes(user_id, limit=20)
            if not quotes:
                self._reply(messaging_api, reply_token, "目前還沒有任何佳句記錄。")
                return
            flex = build_quote_flex_message(quotes)
            self._reply_with_flex(messaging_api, reply_token, None, None, flex)
            return

        if t_lower in ["count", "佳句數量", "quote count"]:
            count = db.count_quotes(user_id)
            self._reply(messaging_api, reply_token, f"目前已記錄 {count} 筆佳句。")
            return

        if t_lower.startswith("編輯佳句 "):
            try:
                quote_id = int(text[4:].strip())
                quote = db.get_quote(user_id, quote_id)
                if not quote:
                    self._reply(messaging_api, reply_token, f"找不到編號 {quote_id} 的佳句。")
                    return
                state = {
                    "module": "quote",
                    "action": "edit_quote",
                    "quote_id": quote_id,
                    "stage": "awaiting_content",
                }
                core_db.set_user_state(user_id, state)
                self._reply(messaging_api, reply_token, "請輸入新的佳句內容：")
            except Exception:
                self._reply(messaging_api, reply_token, "格式錯誤。請輸入：編輯佳句 5")
            return

        if t_lower.startswith("刪除佳句 "):
            try:
                quote_id = int(text[4:].strip())
                if db.delete_quote(user_id, quote_id):
                    self._reply(messaging_api, reply_token, f"已刪除佳句 #{quote_id}。")
                else:
                    self._reply(messaging_api, reply_token, f"找不到佳句 #{quote_id}。")
            except Exception:
                self._reply(messaging_api, reply_token, "格式錯誤。請輸入：刪除佳句 5")
            return

        if text.startswith("新增佳句"):
            state = {
                "module": "quote",
                "action": "add_quote",
                "stage": "awaiting_content",
                "data": {},
            }
            core_db.set_user_state(user_id, state)
            self._reply(messaging_api, reply_token, "請輸入佳句內容：")
            return

        normalized_text = text.replace("＋", "+")
        if normalized_text.startswith("佳句") and "+" in normalized_text:
            content, source, speaker, tags = self._parse_quote_input(normalized_text)
            quote_id = db.add_quote(user_id, content, source=source, speaker=speaker, tags=tags)
            quote = db.get_quote(user_id, quote_id)
            flex = build_quote_success_flex(quote)
            self._reply_with_flex(messaging_api, reply_token, None, None, flex)
            return

        self._reply(messaging_api, reply_token, "佳句記錄已啟用。輸入 help 查看指令。）")

    def _handle_stateful_message(self, user_id, state, text):
        t = text.strip()
        if t.lower() == "取消":
            core_db.clear_user_state(user_id)
            return "操作已取消。", None, None

        action = state.get("action")
        if action == "add_quote":
            stage = state.get("stage")
            if stage == "awaiting_content":
                state["data"]["content"] = t
                state["stage"] = "awaiting_source"
                core_db.set_user_state(user_id, state)
                return "請輸入出處（可留空）：", None, None
            if stage == "awaiting_source":
                state["data"]["source"] = t or "未填"
                state["stage"] = "awaiting_speaker"
                core_db.set_user_state(user_id, state)
                return "請輸入誰說的（可留空）：", None, None
            if stage == "awaiting_speaker":
                state["data"]["speaker"] = t or "未填"
                state["stage"] = "awaiting_tags"
                core_db.set_user_state(user_id, state)
                return "請輸入標籤（多個用逗號分隔，若無可直接回覆 取消）：", None, None
            if stage == "awaiting_tags":
                quote_id = db.add_quote(
                    user_id,
                    state["data"]["content"],
                    source=state["data"].get("source"),
                    speaker=state["data"].get("speaker"),
                    tags=t,
                )
                core_db.clear_user_state(user_id)
                quote = db.get_quote(user_id, quote_id)
                flex = build_quote_success_flex(quote)
                return None, None, flex

        if action == "edit_quote":
            stage = state.get("stage")
            quote_id = state.get("quote_id")
            if stage == "awaiting_content":
                state["data"] = {"content": t}
                state["stage"] = "awaiting_source"
                core_db.set_user_state(user_id, state)
                return "請輸入新的出處（可留空）：", None, None
            if stage == "awaiting_source":
                state["data"]["source"] = t or "未填"
                state["stage"] = "awaiting_speaker"
                core_db.set_user_state(user_id, state)
                return "請輸入新的誰說的（可留空）：", None, None
            if stage == "awaiting_speaker":
                state["data"]["speaker"] = t or "未填"
                state["stage"] = "awaiting_tags"
                core_db.set_user_state(user_id, state)
                return "請輸入新的標籤（多個用逗號分隔；若不改可輸入 無）：", None, None
            if stage == "awaiting_tags":
                tags = None if t.lower() == "無" else t
                db.update_quote(
                    user_id,
                    quote_id,
                    content=state["data"].get("content"),
                    source=state["data"].get("source"),
                    speaker=state["data"].get("speaker"),
                    tags=tags,
                )
                core_db.clear_user_state(user_id)
                return f"已更新佳句 #{quote_id}。", None, None

        return "對話狀態錯誤，已自動清理。", None, None

    def _parse_quote_input(self, text):
        normalized_text = text.replace("＋", "+")
        parts = [p.strip() for p in normalized_text.split("+") if p.strip()]
        if len(parts) < 2:
            raise ValueError("格式錯誤")
        content = parts[1]
        source = parts[2] if len(parts) >= 3 else "未填"
        speaker = parts[3] if len(parts) >= 4 else "未填"
        tags = []
        for part in parts[4:]:
            if part.startswith("#"):
                tags.extend([tag.strip() for tag in part[1:].split(",") if tag.strip()])
        return content, source, speaker, tags

    def _reply(self, messaging_api, reply_token, reply_text):
        messaging_api.reply_message(
            ReplyMessageRequest(
                replyToken=reply_token,
                messages=[V3TextMessage(text=reply_text)],
            )
        )

    def _reply_with_flex(self, messaging_api, reply_token, reply_text=None, quick_reply=None, flex_content=None):
        messages = []
        if flex_content:
            messages.append(
                FlexMessage(
                    altText="佳句卡片",
                    contents=FlexContainer.from_dict(flex_content),
                    quickReply=quick_reply,
                )
            )
        elif reply_text:
            messages.append(V3TextMessage(text=reply_text, quickReply=quick_reply))

        if messages:
            messaging_api.reply_message(ReplyMessageRequest(replyToken=reply_token, messages=messages))
