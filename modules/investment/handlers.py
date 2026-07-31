# modules/investment/handlers.py
import re
from linebot.v3.messaging.models import ReplyMessageRequest, TextMessage as V3TextMessage, FlexMessage, FlexContainer
from core import database as core_db
from modules.base_module import BaseModule
from modules.investment import models as db
from modules.investment.api import investment_api
from modules.investment.flex_templates import (
    get_quick_reply,
    create_portfolio_summary_flex,
    create_investment_list_flex,
    create_investment_help_flex
)

class InvestmentModule(BaseModule):
    @property
    def name(self) -> str:
        return "investment"

    @property
    def display_name(self) -> str:
        return "📈 投資狀態記錄"

    def get_blueprint(self):
        return investment_api

    def handle_postback(self, messaging_api, event, user_id: str, postback_data: str, reply_token: str):
        pass

    def handle_message(self, messaging_api, event, user_id: str, text: str, reply_token: str):
        text = text.strip()
        state = core_db.get_user_state(user_id)

        if state and state.get("module") == "investment":
            reply_text, quick_reply, flex_content = self._handle_stateful_message(user_id, state, text)
            self._reply(messaging_api, reply_token, reply_text, quick_reply, flex_content)
            return

        if "+" in text and ("買入" in text or "投資" in text):
            reply_text, quick_reply, flex_content = self._handle_shortcut_add(user_id, text)
            self._reply(messaging_api, reply_token, reply_text, quick_reply, flex_content)
            return

        reply_text, quick_reply, flex_content = self._handle_command(user_id, text)
        self._reply(messaging_api, reply_token, reply_text, quick_reply, flex_content)

    def _reply(self, messaging_api, reply_token, reply_text=None, quick_reply=None, flex_content=None):
        messages = []
        if flex_content:
            messages.append(FlexMessage(altText="投資記錄通知", contents=FlexContainer.from_dict(flex_content), quickReply=quick_reply))
        elif reply_text:
            messages.append(V3TextMessage(text=reply_text, quickReply=quick_reply))

        if messages:
            messaging_api.reply_message(ReplyMessageRequest(replyToken=reply_token, messages=messages))

    def _handle_shortcut_add(self, user_id, text):
        # 範例：投資 + 台股 + 2330 台積電 + 買入 1000 @ 600
        parts = [p.strip() for p in text.split("+") if p.strip()]
        try:
            asset_type = "台股"
            symbol_name = ""
            details = ""

            if len(parts) >= 4:
                asset_type = parts[1]
                symbol_name = parts[2]
                details = parts[3]
            elif len(parts) == 3:
                symbol_name = parts[1]
                details = parts[2]
            else:
                return "格式錯誤。範例：投資 + 台股 + 2330 台積電 + 買入 1000 @ 600", None, None

            # 解析代碼與名稱
            sn_parts = symbol_name.split(" ", 1)
            symbol = sn_parts[0]
            name = sn_parts[1] if len(sn_parts) > 1 else symbol

            # 解析數量與價格 (買入 1000 @ 600)
            qty_match = re.search(r'(?:買入\s*)?([0-9.]+)', details)
            price_match = re.search(r'@\s*([0-9.]+)', details)

            if not qty_match or not price_match:
                return "未能解析數量或單價。範例：買入 1000 @ 600", None, None

            quantity = float(qty_match.group(1))
            price = float(price_match.group(1))

            asset_id = db.add_or_update_asset(user_id, symbol, name, asset_type, quantity, price)
            summary = db.get_portfolio_summary(user_id)
            flex = create_portfolio_summary_flex(summary)

            return f"成功記錄買入 {symbol} {name}：{quantity} 股 @ ${price}", get_quick_reply([("📊查看總覽", "portfolio"), ("📈持股清單", "資產")]), flex
        except Exception as e:
            return f"新增失敗：{str(e)}", None, None

    def _handle_stateful_message(self, user_id, state, text):
        action = state.get("action"); t = text.strip()
        if t.lower() == "取消":
            core_db.clear_user_state(user_id)
            return "操作已取消。", None, None

        if action == "add_investment":
            stage = state.get("stage")
            if stage == "awaiting_symbol":
                parts = t.split(" ", 1)
                symbol = parts[0].upper()
                name = parts[1] if len(parts) > 1 else symbol
                state["data"]["symbol"] = symbol
                state["data"]["name"] = name
                state["stage"] = "awaiting_qty_price"
                core_db.set_user_state(user_id, state)
                return f"已設定標的：[{symbol} {name}]\n請輸入數量與單價（格式：數量 @ 價格，如：1000 @ 600）：", get_quick_reply(["取消"]), None

            elif stage == "awaiting_qty_price":
                qty_match = re.search(r'([0-9.]+)', t)
                price_match = re.search(r'@\s*([0-9.]+)', t)
                if not qty_match or not price_match:
                    return "格式錯誤，請依格式輸入（如：1000 @ 600）：", get_quick_reply(["取消"]), None

                quantity = float(qty_match.group(1))
                price = float(price_match.group(1))
                data = state["data"]

                asset_id = db.add_or_update_asset(user_id, data["symbol"], data["name"], data.get("asset_type", "台股"), quantity, price)
                core_db.clear_user_state(user_id)

                summary = db.get_portfolio_summary(user_id)
                flex = create_portfolio_summary_flex(summary)
                return f"已成功記錄買入 [{data['symbol']}] {quantity} 股 @ ${price}！", None, flex

        return "操作已清除。", None, None

    def _handle_command(self, user_id, text):
        t = text.strip()
        t_lower = t.lower()

        if t_lower in ["help", "幫助", "說明"]:
            return None, None, create_investment_help_flex()

        if t_lower == "ping":
            return "pong 🏓 投資狀態記錄助手運行中", None, None

        if t_lower in ["portfolio", "總覽", "投資總覽", "資產總覽"]:
            summary = db.get_portfolio_summary(user_id)
            if summary["asset_count"] == 0:
                return "目前尚無投資記錄。點擊下方選單開始新增吧！", get_quick_reply([("➕新增買入", "買入"), ("🔍幫助", "help")]), None
            flex = create_portfolio_summary_flex(summary)
            return None, None, flex

        if t_lower in ["資產", "持股", "股票清單", "明細"]:
            assets = db.list_assets(user_id)
            if not assets:
                return "目前尚無持股明細。", get_quick_reply([("➕新增買入", "買入")]), None
            flex = create_investment_list_flex(assets)
            return None, None, flex

        if t_lower in ["買入", "新增投資"]:
            state = {"module": "investment", "action": "add_investment", "stage": "awaiting_symbol", "data": {"asset_type": "台股"}}
            core_db.set_user_state(user_id, state)
            return "請輸入股票標的代碼與名稱（例如：2330 台積電 或 AAPL 蘋果）：", get_quick_reply(["取消"]), None

        if t.startswith("更新 "):
            # 更新現價語法：更新 2330 650
            parts = t.split(" ", 2)
            if len(parts) >= 3:
                symbol = parts[1].upper()
                try:
                    price = float(parts[2])
                    if db.update_asset_price(user_id, symbol, price):
                        summary = db.get_portfolio_summary(user_id)
                        flex = create_portfolio_summary_flex(summary)
                        return f"標的 [{symbol}] 現價已更新為 ${price}", None, flex
                    else:
                        return f"找不到持股標的 [{symbol}]。", None, None
                except ValueError:
                    return "價格格式錯誤，請輸入數字。", None, None

        if t.startswith("刪除投資 "):
            asset_id_str = t[5:].strip()
            if asset_id_str.isdigit():
                if db.delete_asset(user_id, int(asset_id_str)):
                    summary = db.get_portfolio_summary(user_id)
                    flex = create_portfolio_summary_flex(summary)
                    return f"投資標的 [{asset_id_str}] 已成功刪除。", None, flex
                else:
                    return "刪除失敗，找不到該項目。", None, None

        return "無法識別指令，請輸入 'help' 檢視說明，或輸入 'portfolio' 查看總覽。", None, None
