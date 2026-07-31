# modules/base_module.py
from abc import ABC, abstractmethod

class BaseModule(ABC):
    """
    所有生活助理子模組的抽象基類。
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """模組唯一識別碼 (例: 'todo', 'house_viewing', 'calendar')"""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """模組顯示名稱 (例: '📝 待辦事項', '🏠 看房預約', '📅 日曆行程')"""
        pass

    @abstractmethod
    def handle_message(self, messaging_api, event, user_id: str, text: str, reply_token: str):
        """處理使用者發送的文字訊息"""
        pass

    @abstractmethod
    def handle_postback(self, messaging_api, event, user_id: str, postback_data: str, reply_token: str):
        """處理 LINE Postback 事件"""
        pass

    def get_blueprint(self):
        """回傳該模組的 Flask Blueprint (可選)"""
        return None
