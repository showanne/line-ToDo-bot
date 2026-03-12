# database.py
import os
import re
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Table, Text, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

# --- 初始化配置 ---
Base = declarative_base()

# 取得資料庫配置
app_env = os.getenv("APP_ENV", "development").lower()
database_url = os.getenv("DATABASE_URL", "").strip()

# 優先使用 DATABASE_URL (如 Supabase)，否則回退到 SQLite
if database_url:
    # 1. 處理 Render/Supabase 等平台提供的格式修正
    # SQLAlchemy 必須使用 postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    # 2. 確保使用 psycopg2 驅動程式
    if not database_url.startswith("postgresql+psycopg2://") and database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # 3. 確保有 sslmode=require (Supabase 必備，防止連線遭拒)
    if "sslmode" not in database_url:
        connector = "&" if "?" in database_url else "?"
        database_url += f"{connector}sslmode=require"

    engine_url = database_url
    connect_args = {}
    db_type = "PostgreSQL (Supabase/Production)"
    
    # 隱藏密碼後輸出日誌，方便除錯
    masked_url = re.sub(r':([^/@]+)@', ':****@', engine_url)
    print(f"Connecting to: {masked_url}")
else:
    # 預設開發環境使用 SQLite
    engine_url = "sqlite:///todo.db"
    connect_args = {"check_same_thread": False}
    db_type = "Local SQLite"
    print("Connecting to local SQLite database...")

# 建立引擎 (內建連線池)
# pool_pre_ping=True 會在每次連線前檢查連線是否可用
engine = create_engine(engine_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

# --- 定義資料模型 (Models) ---

item_sub_categories = Table(
    'item_sub_categories', Base.metadata,
    Column('item_id', Integer, ForeignKey('items.id', ondelete='CASCADE'), primary_key=True),
    Column('sub_category_id', Integer, ForeignKey('sub_categories.id', ondelete='CASCADE'), primary_key=True)
)

item_tags = Table(
    'item_tags', Base.metadata,
    Column('item_id', Integer, ForeignKey('items.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    sub_categories = relationship("SubCategory", back_populates="category", cascade="all, delete")
    items = relationship("Item", back_populates="category")

class SubCategory(Base):
    __tablename__ = "sub_categories"
    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    name = Column(String, nullable=False)
    category = relationship("Category", back_populates="sub_categories")

class Tag(Base):
    __tablename__ = "tags"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)

class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id', ondelete='CASCADE'), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    place = Column(String)
    done = Column(Integer, default=0)
    completed_date = Column(String)
    category = relationship("Category", back_populates="items")
    sub_categories = relationship("SubCategory", secondary=item_sub_categories, backref="items")
    tags = relationship("Tag", secondary=item_tags, backref="items")

class UserState(Base):
    __tablename__ = "user_states"
    user_id = Column(String, primary_key=True, index=True)
    state_data = Column(JSON, nullable=False)

# --- 資料庫操作介面 (API) ---

def init_db():
    """初始化資料表結構"""
    try:
        Base.metadata.create_all(bind=engine)
        print(f"Database initialized ({app_env}): {db_type}")
    except Exception as e:
        print(f"DATABASE ERROR during init_db: {str(e)}")
        # 拋出異常讓啟動流程失敗，以便在日誌中看到完整 Traceback
        raise e

def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.flush()
        return instance

def set_user_state(user_id, state_dict):
    session = db_session()
    try:
        state = session.query(UserState).filter(UserState.user_id == user_id).first()
        if state:
            state.state_data = state_dict
        else:
            state = UserState(user_id=user_id, state_data=state_dict)
            session.add(state)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

def get_user_state(user_id):
    session = db_session()
    try:
        state = session.query(UserState).filter(UserState.user_id == user_id).first()
        return state.state_data if state else None
    finally:
        session.close()

def clear_user_state(user_id):
    session = db_session()
    try:
        session.query(UserState).filter(UserState.user_id == user_id).delete()
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

def add_item(user_id, category_name, sub_category_names, title, tags=None, place=None):
    session = db_session()
    try:
        cat = get_or_create(session, Category, user_id=user_id, name=category_name)
        if isinstance(sub_category_names, str):
            sub_category_names = [s.strip() for s in sub_category_names.split(",") if s.strip()]
        sub_cats = []
        for sc_name in sub_category_names:
            sub_cats.append(get_or_create(session, SubCategory, category_id=cat.id, name=sc_name))
        item_tags_list = []
        if tags:
            for t_name in tags:
                item_tags_list.append(get_or_create(session, Tag, user_id=user_id, name=t_name))
        new_item = Item(
            user_id=user_id,
            category_id=cat.id,
            title=title,
            place=place,
            done=0,
            sub_categories=sub_cats,
            tags=item_tags_list
        )
        session.add(new_item)
        session.commit()
        return new_item.id
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_item(user_id, item_ids):
    session = db_session()
    try:
        count = session.query(Item).filter(Item.id.in_(item_ids), Item.user_id == user_id).delete(synchronize_session=False)
        session.commit()
        return count
    except Exception:
        session.rollback()
        return 0
    finally:
        session.close()

def mark_item_as_done(user_id, item_ids):
    session = db_session()
    try:
        items = session.query(Item).filter(Item.id.in_(item_ids), Item.user_id == user_id).all()
        for item in items:
            item.done = 1
            item.completed_date = datetime.now().isoformat()
        session.commit()
        return len(items)
    except Exception:
        session.rollback()
        return 0
    finally:
        session.close()

def get_item(user_id, item_id):
    session = db_session()
    try:
        item = session.query(Item).filter(Item.id == item_id, Item.user_id == user_id).first()
        if not item: return None
        return {
            "id": item.id,
            "title": item.title,
            "place": item.place,
            "category_name": item.category.name,
            "sub_category_names": ", ".join([sc.name for sc in item.sub_categories]),
            "tag_names": ", ".join([t.name for t in item.tags])
        }
    finally:
        session.close()

def edit_item(user_id, item_id, field, value):
    session = db_session()
    try:
        item = session.query(Item).filter(Item.id == item_id, Item.user_id == user_id).first()
        if not item: return False
        if field == "title": item.title = value
        elif field == "place": item.place = value
        else: return False
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()

def list_items(user_id, category_name=None, sub_category_name=None, tag_name=None, place=None):
    session = db_session()
    try:
        query = session.query(Item).join(Category).filter(Item.user_id == user_id)
        if category_name:
            query = query.filter(Category.name == category_name)
        if sub_category_name:
            query = query.join(Item.sub_categories).filter(SubCategory.name == sub_category_name)
        if tag_name:
            query = query.join(Item.tags).filter(Tag.name == tag_name)
        if place:
            query = query.filter(Item.place == place)
            
        items = query.order_by(Category.name, Item.id).all()
        results = []
        for i in items:
            sub_cats = ", ".join([sc.name for sc in i.sub_categories])
            tag_str = ", ".join([t.name for t in i.tags])
            results.append((
                i.id, i.title, i.description, i.done, i.place, 
                i.completed_date, i.category.name, sub_cats, tag_str
            ))
        return results
    finally:
        session.close()

def list_categories(user_id):
    session = db_session()
    try:
        categories = session.query(Category.name).filter(Category.user_id == user_id).distinct().all()
        return [c[0] for c in categories]
    finally:
        session.close()

def list_tags(user_id):
    session = db_session()
    try:
        tags = session.query(Tag.name).filter(Tag.user_id == user_id).distinct().all()
        return [t[0] for t in tags]
    finally:
        session.close()

def list_places(user_id):
    session = db_session()
    try:
        # 地點直接存於 Item 表中
        places = session.query(Item.place).filter(Item.user_id == user_id, Item.place != None).distinct().all()
        return [p[0] for p in places if p[0]]
    finally:
        session.close()

def list_sub_categories(user_id, category_name=None):
    session = db_session()
    try:
        query = session.query(Category.name, SubCategory.name).join(SubCategory).filter(Category.user_id == user_id)
        if category_name:
            query = query.filter(Category.name == category_name)
        results = query.order_by(Category.name, SubCategory.name).distinct().all()
        return results
    finally:
        session.close()

def rename_category(user_id, old_name, new_name):
    session = db_session()
    try:
        cat = session.query(Category).filter(Category.user_id == user_id, Category.name == old_name).first()
        if not cat: return False
        cat.name = new_name
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()

def rename_sub_category(user_id, category_name, old_name, new_name):
    session = db_session()
    try:
        cat = session.query(Category).filter(Category.user_id == user_id, Category.name == category_name).first()
        if not cat: return False
        sub_cat = session.query(SubCategory).filter(SubCategory.category_id == cat.id, SubCategory.name == old_name).first()
        if not sub_cat: return False
        sub_cat.name = new_name
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()
