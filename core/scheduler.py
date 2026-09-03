# core/scheduler.py
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text
from core.database import engine

def keep_supabase_alive():
    """每隔幾天執行一次簡單查詢，防止 Supabase 被暫停"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        print(f"[{datetime.now()}] Successfully pinged Supabase to keep it alive.")
    except Exception as e:
        print(f"[{datetime.now()}] Error pinging database: {e}")

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(func=keep_supabase_alive, trigger="interval", days=6)
except Exception:
    scheduler = None

def start_scheduler():
    if scheduler and not getattr(scheduler, "running", False):
        try:
            scheduler.start()
            print("Background scheduler started.")
        except Exception as e:
            print(f"Background scheduler skipped in serverless environment: {e}")
