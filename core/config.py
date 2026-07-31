# core/config.py
import os
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
APP_ENV = os.getenv("APP_ENV", "development").lower()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not CHANNEL_ACCESS_TOKEN or not CHANNEL_SECRET:
    raise RuntimeError("請在 .env 設定 LINE_CHANNEL_ACCESS_TOKEN 與 LINE_CHANNEL_SECRET")
