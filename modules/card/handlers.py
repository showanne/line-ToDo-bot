from linebot.v3.messaging.models import ReplyMessageRequest, TextMessage as V3TextMessage, FlexMessage, FlexContainer

from core import database as core_db
from modules.base_module import BaseModule
from modules.card import models as db
from modules.card.api import card_api
from modules.card.flex_templates import create_card_flex, create_card_help_flex


class CardModule(BaseModule):
    @property
    def name(self) -> str:
        return "card"

    @property
    def display_name(self) -> str:
        return "👔 個人名片"

    def get_blueprint(self):
        return card_api

    def handle_postback(self, messaging_api, event, user_id: str, postback_data: str, reply_token: str):
        if postback_data.startswith("edit_card:"):
            state = {
                "module": "card",
                "action": "edit_card",
                "stage": "awaiting_name",
                "data": {},
            }
            core_db.set_user_state(user_id, state)
            self._reply(messaging_api, reply_token, "請輸入姓名：")
            return

        if postback_data.startswith("share_card:"):
            recipient = postback_data.split(":", 1)[1].strip()
            profile = db.get_profile(user_id)
            share_id = db.record_share(user_id, recipient, profile)
            self._reply(messaging_api, reply_token, f"已紀錄名片分享給 {recipient}（記錄 #{share_id}）")

    def handle_message(self, messaging_api, event, user_id: str, text: str, reply_token: str):
        text = text.strip()
        state = core_db.get_user_state(user_id)

        if state and state.get("module") == "card":
            reply_text, flex_content = self._handle_stateful_message(user_id, state, text)
            self._reply_with_flex(messaging_api, reply_token, reply_text, flex_content)
            return

        t_lower = text.lower()
        if t_lower in ["help", "幫助", "說明", "指令"]:
            self._reply_with_flex(messaging_api, reply_token, None, create_card_help_flex())
            return

        if t_lower in ["card", "名片", "我的名片", "show card"]:
            profile = db.get_profile(user_id)
            self._reply_with_flex(messaging_api, reply_token, None, create_card_flex(profile))
            return

        if text.startswith("編輯名片"):
            state = {
                "module": "card",
                "action": "edit_card",
                "stage": "awaiting_name",
                "data": {},
            }
            core_db.set_user_state(user_id, state)
            self._reply(messaging_api, reply_token, "請輸入姓名：")
            return

        if text.startswith("分享名片"):
            recipient = text.replace("分享名片", "", 1).strip()
            if not recipient:
                self._reply(messaging_api, reply_token, "格式錯誤。請輸入：分享名片 <recipient_user_id>")
                return
            profile = db.get_profile(user_id)
            share_id = db.record_share(user_id, recipient, profile)
            flex = create_card_flex(profile)
            self._reply_with_flex(messaging_api, reply_token, f"已將名片分享給 {recipient}（記錄 #{share_id}）", flex)
            return

        self._reply(messaging_api, reply_token, "名片模組已啟用。輸入 help 查看指令。")

    def _handle_stateful_message(self, user_id, state, text):
        t = text.strip()
        if t.lower() == "取消":
            core_db.clear_user_state(user_id)
            return "操作已取消。", None

        action = state.get("action")
        if action == "edit_card":
            stage = state.get("stage")
            if stage == "awaiting_name":
                state["data"]["name"] = t
                state["stage"] = "awaiting_title"
                core_db.set_user_state(user_id, state)
                return "請輸入職稱：", None
            if stage == "awaiting_title":
                state["data"]["title"] = t
                state["stage"] = "awaiting_company"
                core_db.set_user_state(user_id, state)
                return "請輸入公司名稱：", None
            if stage == "awaiting_company":
                state["data"]["company"] = t
                state["stage"] = "awaiting_phone"
                core_db.set_user_state(user_id, state)
                return "請輸入電話：", None
            if stage == "awaiting_phone":
                state["data"]["phone"] = t
                state["stage"] = "awaiting_email"
                core_db.set_user_state(user_id, state)
                return "請輸入 Email：", None
            if stage == "awaiting_email":
                state["data"]["email"] = t
                state["stage"] = "awaiting_website"
                core_db.set_user_state(user_id, state)
                return "請輸入網站（可留空）：", None
            if stage == "awaiting_website":
                state["data"]["website"] = t or "未填寫"
                state["stage"] = "awaiting_note"
                core_db.set_user_state(user_id, state)
                return "請輸入備註（可留空）：", None
            if stage == "awaiting_note":
                state["data"]["note"] = t or "未填寫"
                db.upsert_profile(user_id, state["data"])
                core_db.clear_user_state(user_id)
                flex = create_card_flex(state["data"])
                return "已更新名片內容。", flex

        return "對話狀態錯誤，已自動清理。", None

    def _reply(self, messaging_api, reply_token, reply_text):
        messaging_api.reply_message(ReplyMessageRequest(replyToken=reply_token, messages=[V3TextMessage(text=reply_text)]))

    def _reply_with_flex(self, messaging_api, reply_token, reply_text=None, flex_content=None):
        messages = []
        if flex_content:
            messages.append(FlexMessage(altText="個人名片", contents=FlexContainer.from_dict(flex_content)))
        if reply_text:
            messages.append(V3TextMessage(text=reply_text))
        if messages:
            messaging_api.reply_message(ReplyMessageRequest(replyToken=reply_token, messages=messages))
