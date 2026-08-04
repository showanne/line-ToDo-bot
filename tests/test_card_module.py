import os
import unittest

os.environ["DATABASE_URL"] = "sqlite:///test_card.db"

from core import database as core_db
from core.database import init_db
from modules.card import models as db


init_db()


class CardModuleModelTest(unittest.TestCase):
    def test_save_and_get_card_profile(self):
        user_id = "test-user-card"
        payload = {
            "name": "小安",
            "title": "前端工程師",
            "company": "LINE Bot Lab",
            "phone": "0912345678",
            "email": "anne@example.com",
            "website": "https://anne.example.com",
            "note": "喜歡分享技術"
        }
        db.upsert_profile(user_id, payload)
        profile = db.get_profile(user_id)
        self.assertEqual(profile["name"], "小安")
        self.assertEqual(profile["company"], "LINE Bot Lab")

    def tearDown(self):
        core_db.db_session.remove()
        db.engine.dispose()
        if os.path.exists("test_card.db"):
            try:
                os.remove("test_card.db")
            except PermissionError:
                pass

    def test_record_share_logs_recipient(self):
        sender = "sender-001"
        recipient = "recipient-002"
        payload = {
            "name": "小安",
            "title": "前端工程師",
            "company": "LINE Bot Lab"
        }
        share_id = db.record_share(sender, recipient, payload)
        self.assertIsNotNone(share_id)
        history = db.list_share_history(sender, limit=5)
        self.assertGreaterEqual(len(history), 1)
        self.assertEqual(history[0]["recipient_user_id"], recipient)


if __name__ == "__main__":
    unittest.main()
