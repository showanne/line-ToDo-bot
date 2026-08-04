# core/router.py
from linebot.v3.messaging.models import ReplyMessageRequest, TextMessage as V3TextMessage
from core import database as core_db
from modules.todo.handlers import TodoModule
from modules.investment.handlers import InvestmentModule
from modules.quote.handlers import QuoteModule
from modules.card.handlers import CardModule

class MessageRouter:
    """
    生活助理平台門禁分流器 (The Door / Message Router)。
    負責根據使用者的 active_mode 將訊息分派至對應的子模組。
    """
    def __init__(self):
        self.modules = {
            "todo": TodoModule(),
            "investment": InvestmentModule(),
            "quote": QuoteModule(),
            "card": CardModule()
        }
        # 模組切換指令映射
        self.mode_switches = {
            "@待辦": "todo",
            "切換模式:待辦": "todo",
            "mode:todo": "todo",
            "@投資": "investment",
            "切換模式:投資": "investment",
            "mode:investment": "investment",
            "@看房": "house_viewing",
            "切換模式:看房": "house_viewing",
            "mode:house_viewing": "house_viewing",
            "@日曆": "calendar",
            "切換模式:日曆": "calendar",
            "mode:calendar": "calendar",
            "@佳句": "quote",
            "切換模式:佳句": "quote",
            "mode:quote": "quote",
            "@名片": "card",
            "切換模式:名片": "card",
            "mode:card": "card"
        }

    def register_module(self, module):
        self.modules[module.name] = module

    def dispatch_message(self, messaging_api, event, user_id: str, text: str, reply_token: str):
        text_strip = text.strip()

        # 1. 檢查是否為「切換模組」的門禁指令
        if text_strip in self.mode_switches:
            target_mode = self.mode_switches[text_strip]
            core_db.set_user_active_mode(user_id, target_mode)

            mode_names = {
                "todo": "📝 待辦清單",
                "investment": "📈 投資狀態記錄",
                "house_viewing": "🏠 看房預約助手",
                "calendar": "📅 日曆事件機器人",
                "quote": "💬 佳句記錄",
                "card": "👔 個人名片"
            }
            display_name = mode_names.get(target_mode, target_mode)
            msg = f"已切換至【{display_name}】模式！"
            if target_mode not in self.modules:
                msg += "\n(此模組建置中，敬請期待)"

            messaging_api.reply_message(
                ReplyMessageRequest(
                    replyToken=reply_token,
                    messages=[V3TextMessage(text=msg)]
                )
            )
            return

        # 2. 取得使用者當前模式
        active_mode = core_db.get_user_active_mode(user_id)

        # 3. 分派給對應模組處理；若未找到對應模組，預設退回 todo
        module = self.modules.get(active_mode, self.modules.get("todo"))
        if module:
            module.handle_message(messaging_api, event, user_id, text, reply_token)
        else:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    replyToken=reply_token,
                    messages=[V3TextMessage(text="系統異常：找不到當前模式之處理模組。")]
                )
            )

    def dispatch_postback(self, messaging_api, event, user_id: str, postback_data: str, reply_token: str):
        active_mode = core_db.get_user_active_mode(user_id)
        module = self.modules.get(active_mode, self.modules.get("todo"))
        if module:
            module.handle_postback(messaging_api, event, user_id, postback_data, reply_token)
