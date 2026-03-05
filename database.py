# database.py
import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Table, Text, JSON
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

# --- 初始化配置 ---
Base = declarative_base()

# 取得資料庫配置
app_env = os.getenv("APP_ENV", "development").lower()
database_url = os.getenv("DATABASE_URL")

# 依據環境變數 (APP_ENV) 決定資料庫類型
if app_env == "production" and database_url:
    # 處理 Heroku 等平台提供的 postgres:// 格式修正
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    engine_url = database_url
    connect_args = {}
else:
    # 開發環境 (development) 預設使用 SQLite
    engine_url = "sqlite:///todo.db"
    # SQLite 特殊設定: 支援多執行緒存取
    connect_args = {"check_same_thread": False}

# 建立引擎 (內建連線池)
engine = create_engine(engine_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db_session = scoped_session(SessionLocal)

# --- 定義資料模型 (Models) ---

# 多對多關聯表 (Association Tables)
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
    done = Column(Integer, default=0) # 修正：改為 Integer 以符合 PostgreSQL 現有結構 (0:未完成, 1:已完成)
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
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized ({app_env}): {engine_url.split('@')[-1] if '@' in engine_url else engine_url}")

def get_or_create(session, model, **kwargs):
    """通用輔助函式: 獲取資料，若不存在則建立"""
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.flush() # 確保取得 ID
        return instance

def set_user_state(user_id, state_dict):
    """持久化保存使用者對話狀態"""
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
    """取得持久化的使用者對話狀態"""
    session = db_session()
    try:
        state = session.query(UserState).filter(UserState.user_id == user_id).first()
        return state.state_data if state else None
    finally:
        session.close()

def clear_user_state(user_id):
    """清空使用者對話狀態"""
    session = db_session()
    try:
        session.query(UserState).filter(UserState.user_id == user_id).delete()
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

def add_item(user_id, category_name, sub_category_names, title, tags=None, place=None):
    """新增待辦事項"""
    session = db_session()
    try:
        # 取得或建立主分類
        cat = get_or_create(session, Category, user_id=user_id, name=category_name)
        
        # 處理子分類
        if isinstance(sub_category_names, str):
            sub_category_names = [s.strip() for s in sub_category_names.split(",") if s.strip()]
        
        sub_cats = []
        for sc_name in sub_category_names:
            sub_cats.append(get_or_create(session, SubCategory, category_id=cat.id, name=sc_name))
            
        # 處理標籤
        item_tags_list = []
        if tags:
            for t_name in tags:
                item_tags_list.append(get_or_create(session, Tag, user_id=user_id, name=t_name))
        
        # 建立項目
        new_item = Item(
            user_id=user_id,
            category_id=cat.id,
            title=title,
            place=place,
            done=0, # 確保使用整數
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
    """刪除項目"""
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
    """標記完成"""
    session = db_session()
    try:
        items = session.query(Item).filter(Item.id.in_(item_ids), Item.user_id == user_id).all()
        for item in items:
            item.done = 1 # 修正：使用整數 1
            item.completed_date = datetime.now().isoformat()
        session.commit()
        return len(items)
    except Exception:
        session.rollback()
        return 0
    finally:
        session.close()

def get_item(user_id, item_id):
    """獲取單一項目詳細資訊 (轉換為字典相容格式)"""
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
    """編輯項目欄位"""
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

def list_items(user_id, category_name=None, sub_category_name=None):
    """列出清單，回傳相容於原 app.py 的 Tuple 格式"""
    session = db_session()
    try:
        # 基礎查詢，先 JOIN Category 方便後續過濾與排序
        query = session.query(Item).join(Category).filter(Item.user_id == user_id)
        
        if category_name:
            query = query.filter(Category.name == category_name)
            
        if sub_category_name:
            # 這裡 JOIN SubCategory 沒問題，因為它是不同資料表
            query = query.join(Item.sub_categories).filter(SubCategory.name == sub_category_name)
            
        # 排序: 主分類、ID
        items = query.order_by(Category.name, Item.id).all()
        
        # 轉換為 Tuple 格式以維持 app.py 的相容性
        results = []
        for i in items:
            sub_cats = ", ".join([sc.name for sc in i.sub_categories])
            tag_str = ", ".join([t.name for t in i.tags])
            # i.done 現在已經是整數了，直接放入即可
            results.append((
                i.id, i.title, i.description, i.done, i.place, 
                i.completed_date, i.category.name, sub_cats, tag_str
            ))
        return results
    finally:
        session.close()

def list_categories(user_id):
    """列出使用者的所有主分類名稱"""
    session = db_session()
    try:
        categories = session.query(Category.name).filter(Category.user_id == user_id).distinct().all()
        return [c[0] for c in categories]
    finally:
        session.close()

def list_sub_categories(user_id, category_name=None):
    """列出使用者的所有子分類名稱，回傳 (主分類, 子分類) 列表"""
    session = db_session()
    try:
        query = session.query(Category.name, SubCategory.name).join(SubCategory).filter(Category.user_id == user_id)
        if category_name:
            query = query.filter(Category.name == category_name)
        results = query.order_by(Category.name, SubCategory.name).distinct().all()
        return results
    finally:
        session.close()
