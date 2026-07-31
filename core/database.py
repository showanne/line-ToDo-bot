# core/database.py
import os
from sqlalchemy import create_engine, Column, String, JSON
from sqlalchemy.orm import declarative_base, sessionmaker, scoped_session
from core.config import APP_ENV, DATABASE_URL

Base = declarative_base()

# 取得資料庫連線配置
if DATABASE_URL:
    url = DATABASE_URL
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if "sslmode" not in url:
        url += ("&" if "?" in url else "?") + "sslmode=require"
    engine_url = url
    connect_args = {"connect_timeout": 10}
    db_type = "PostgreSQL (Supabase/Production)"
else:
    engine_url = "sqlite:///todo.db"
    connect_args = {"check_same_thread": False}
    db_type = "Local SQLite"

engine = create_engine(engine_url, connect_args=connect_args, pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

# --- 平台全域核心模型 ---

class UserState(Base):
    __tablename__ = "user_states"
    user_id = Column(String, primary_key=True, index=True)
    state_data = Column(JSON, nullable=False)

class UserContext(Base):
    __tablename__ = "user_contexts"
    user_id = Column(String, primary_key=True, index=True)
    active_mode = Column(String, default="todo", nullable=False)

# --- 核心 Helper 函式 ---

def run_migrations():
    """執行 Alembic 資料庫遷移"""
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    try:
        command.upgrade(alembic_cfg, "head")
        print("Alembic migrations applied successfully.")
    except Exception as e:
        print(f"Error applying migrations: {e}")

def init_db():
    """初始化所有模型資料表並套用遷移"""
    Base.metadata.create_all(bind=engine)
    run_migrations()
    print(f"Database initialized ({APP_ENV}): {db_type}")

def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance: return instance
    instance = model(**kwargs)
    session.add(instance)
    session.flush()
    return instance

# --- 使用者對話狀態管理 ---

def set_user_state(user_id, state_dict):
    session = db_session()
    try:
        state = session.query(UserState).filter(UserState.user_id == user_id).first()
        if state: state.state_data = state_dict
        else: session.add(UserState(user_id=user_id, state_data=state_dict))
        session.commit()
    except: session.rollback()
    finally: session.close()

def get_user_state(user_id):
    session = db_session()
    try:
        state = session.query(UserState).filter(UserState.user_id == user_id).first()
        return state.state_data if state else None
    finally: session.close()

def clear_user_state(user_id):
    session = db_session()
    try:
        session.query(UserState).filter(UserState.user_id == user_id).delete()
        session.commit()
    except: session.rollback()
    finally: session.close()

# --- 使用者子助理模式 (Active Mode) 管理 ---

def get_user_active_mode(user_id):
    session = db_session()
    try:
        ctx = session.query(UserContext).filter(UserContext.user_id == user_id).first()
        return ctx.active_mode if ctx and ctx.active_mode else "todo"
    finally:
        session.close()

def set_user_active_mode(user_id, mode):
    session = db_session()
    try:
        ctx = session.query(UserContext).filter(UserContext.user_id == user_id).first()
        if ctx:
            ctx.active_mode = mode
        else:
            session.add(UserContext(user_id=user_id, active_mode=mode))
        session.commit()
        return True
    except:
        session.rollback()
        return False
    finally:
        session.close()
