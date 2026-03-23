# database.py
import os
import re
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, Table, Text, JSON, func, case, text, inspect
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, scoped_session

# --- 初始化配置 ---
Base = declarative_base()

# 取得資料庫配置
app_env = os.getenv("APP_ENV", "development").lower()
database_url = os.getenv("DATABASE_URL", "").strip()

if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if "sslmode" not in database_url:
        database_url += ("&" if "?" in database_url else "?") + "sslmode=require"
    engine_url = database_url
    connect_args = {"connect_timeout": 10}
    db_type = "PostgreSQL (Supabase/Production)"
else:
    engine_url = "sqlite:///todo.db"
    connect_args = {"check_same_thread": False}
    db_type = "Local SQLite"

engine = create_engine(engine_url, connect_args=connect_args, pool_pre_ping=True, pool_recycle=300)
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
    is_deleted = Column(Integer, default=0) # 0: 正常, 1: 已刪除
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
    Base.metadata.create_all(bind=engine)
    
    # 檢查並補齊缺失的欄位 (適用於已存在的資料庫)
    inspector = inspect(engine)
    if 'items' in inspector.get_table_names():
        columns = {c['name'] for c in inspector.get_columns('items')}
        
        with engine.begin() as conn:
            # 1. 補齊 is_deleted 欄位
            if 'is_deleted' not in columns:
                print(f"Adding missing 'is_deleted' column to 'items' table ({db_type})...")
                conn.execute(text("ALTER TABLE items ADD COLUMN is_deleted INTEGER DEFAULT 0"))
            
            # 2. 補齊 description 欄位 (處理舊版可能是 desc 的情況)
            if 'description' not in columns:
                if 'desc' in columns:
                    print(f"Renaming 'desc' to 'description' in 'items' table ({db_type})...")
                    if db_type == "Local SQLite":
                        # SQLite 舊版本不支援 RENAME COLUMN，直接新增並遷移資料
                        conn.execute(text("ALTER TABLE items ADD COLUMN description TEXT"))
                        conn.execute(text("UPDATE items SET description = desc"))
                    else:
                        conn.execute(text("ALTER TABLE items RENAME COLUMN desc TO description"))
                else:
                    print(f"Adding missing 'description' column to 'items' table ({db_type})...")
                    conn.execute(text("ALTER TABLE items ADD COLUMN description TEXT"))
            
            # 3. 補齊 completed_date 欄位
            if 'completed_date' not in columns:
                print(f"Adding missing 'completed_date' column to 'items' table ({db_type})...")
                conn.execute(text("ALTER TABLE items ADD COLUMN completed_date TEXT"))

    print(f"Database initialized ({app_env}): {db_type}")

def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance: return instance
    instance = model(**kwargs)
    session.add(instance)
    session.flush()
    return instance

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

def add_item(user_id, category_name, sub_category_names, title, tags=None, place=None):
    session = db_session()
    try:
        cat = get_or_create(session, Category, user_id=user_id, name=category_name)
        if isinstance(sub_category_names, str):
            sub_category_names = [s.strip() for s in sub_category_names.split(",") if s.strip()]
        sub_cats = [get_or_create(session, SubCategory, category_id=cat.id, name=sc) for sc in sub_category_names]
        tag_objs = [get_or_create(session, Tag, user_id=user_id, name=t) for t in (tags or [])]
        new_item = Item(user_id=user_id, category_id=cat.id, title=title, place=place, done=0, sub_categories=sub_cats, tags=tag_objs)
        session.add(new_item); session.commit()
        return new_item.id
    except Exception as e: session.rollback(); raise e
    finally: session.close()

def delete_item(user_id, item_ids):
    session = db_session()
    try:
        items = session.query(Item).filter(Item.id.in_(item_ids), Item.user_id == user_id).all()
        for i in items: i.is_deleted = 1
        session.commit(); return len(items)
    except: session.rollback(); return 0
    finally: session.close()

def restore_item(user_id, item_ids):
    session = db_session()
    try:
        items = session.query(Item).filter(Item.id.in_(item_ids), Item.user_id == user_id).all()
        for i in items: i.is_deleted = 0
        session.commit(); return len(items)
    except: session.rollback(); return 0
    finally: session.close()

def mark_item_as_done(user_id, item_ids):
    session = db_session()
    try:
        items = session.query(Item).filter(Item.id.in_(item_ids), Item.user_id == user_id, Item.is_deleted == 0).all()
        for i in items: i.done = 1; i.completed_date = datetime.now().isoformat()
        session.commit(); return len(items)
    except: session.rollback(); return 0
    finally: session.close()

def get_item(user_id, item_id):
    session = db_session()
    try:
        i = session.query(Item).filter(Item.id == item_id, Item.user_id == user_id, Item.is_deleted == 0).first()
        if not i: return None
        return {"id": i.id, "title": i.title, "place": i.place, "category_name": i.category.name,
                "sub_category_names": ", ".join([sc.name for sc in i.sub_categories]),
                "tag_names": ", ".join([t.name for t in i.tags])}
    finally: session.close()

def edit_item(user_id, item_id, field, value):
    session = db_session()
    try:
        i = session.query(Item).filter(Item.id == item_id, Item.user_id == user_id, Item.is_deleted == 0).first()
        if not i: return False
        if field == "title": i.title = value
        elif field == "place": i.place = value
        session.commit(); return True
    except: session.rollback(); return False
    finally: session.close()

def list_items(user_id, category_name=None, sub_category_name=None, tag_name=None, place=None, item_ids=None, include_deleted=False):
    session = db_session()
    try:
        query = session.query(Item).join(Category).filter(Item.user_id == user_id)
        if not include_deleted: query = query.filter(Item.is_deleted == 0)
        if category_name: query = query.filter(Category.name == category_name)
        if sub_category_name: query = query.join(Item.sub_categories).filter(SubCategory.name == sub_category_name)
        if tag_name: query = query.join(Item.tags).filter(Tag.name == tag_name)
        if place: query = query.filter(Item.place == place)
        if item_ids: query = query.filter(Item.id.in_(item_ids))
        items = query.order_by(Category.name, Item.id).all()
        return [(i.id, i.title, i.description, i.done, i.place, i.completed_date, i.category.name,
                 ", ".join([sc.name for sc in i.sub_categories]), ", ".join([t.name for t in i.tags])) for i in items]
    finally: session.close()

def list_categories(user_id):
    session = db_session()
    try:
        # 統計各主分類下未完成 (done=0) 的事項數 (排除已刪除)
        results = session.query(
            Category.name,
            func.count(case(((Item.done == 0) & (Item.is_deleted == 0), 1)))
        ).outerjoin(Item, (Item.category_id == Category.id) & (Item.user_id == user_id)) \
         .filter(Category.user_id == user_id) \
         .group_by(Category.name).all()
        return results # [(name, count), ...]
    finally:
        session.close()

def list_sub_categories(user_id, category_name=None):
    session = db_session()
    try:
        # 統計各子分類下未完成的事項數 (排除已刪除)
        query = session.query(
            Category.name,
            SubCategory.name,
            func.count(case(((Item.done == 0) & (Item.is_deleted == 0), 1)))
        ).join(SubCategory, Category.id == SubCategory.category_id) \
         .outerjoin(item_sub_categories, SubCategory.id == item_sub_categories.c.sub_category_id) \
         .outerjoin(Item, (Item.id == item_sub_categories.c.item_id) & (Item.user_id == user_id)) \
         .filter(Category.user_id == user_id)
        
        if category_name:
            query = query.filter(Category.name == category_name)
            
        results = query.group_by(Category.name, SubCategory.name).order_by(Category.name, SubCategory.name).all()
        return results # [(cat_name, sub_name, count), ...]
    finally:
        session.close()

def list_tags(user_id):
    session = db_session()
    try:
        # 統計各標籤下未完成的事項數 (排除已刪除)
        results = session.query(
            Tag.name,
            func.count(case(((Item.done == 0) & (Item.is_deleted == 0), 1)))
        ).outerjoin(item_tags, Tag.id == item_tags.c.tag_id) \
         .outerjoin(Item, (Item.id == item_tags.c.item_id) & (Item.user_id == user_id)) \
         .filter(Tag.user_id == user_id) \
         .group_by(Tag.name).all()
        return results # [(name, count), ...]
    finally:
        session.close()

def list_places(user_id):
    session = db_session()
    try:
        # 統計各個地點下未完成的事項數 (排除已刪除)
        results = session.query(
            Item.place,
            func.count(case(((Item.done == 0) & (Item.is_deleted == 0), 1)))
        ).filter(Item.user_id == user_id, Item.place != None) \
         .group_by(Item.place).all()
        return [r for r in results if r[0]] # [(name, count), ...]
    finally:
        session.close()

def rename_category(user_id, old, new):
    session = db_session(); cat = session.query(Category).filter(Category.user_id == user_id, Category.name == old).first()
    if not cat: return False
    cat.name = new; session.commit(); return True

def rename_sub_category(user_id, cat_name, old, new):
    session = db_session(); cat = session.query(Category).filter(Category.user_id == user_id, Category.name == cat_name).first()
    if not cat: return False
    sc = session.query(SubCategory).filter(SubCategory.category_id == cat.id, SubCategory.name == old).first()
    if not sc: return False
    sc.name = new; session.commit(); return True

def export_data_as_sql():
    """
    匯出所有資料表內容並轉換為 SQL INSERT 語句。
    """
    session = db_session()
    sql_statements = []
    
    # 定義要處理的表與對應的 Model
    tables = [
        (Category, "categories"),
        (SubCategory, "sub_categories"),
        (Tag, "tags"),
        (Item, "items")
    ]
    
    try:
        # 1. 處理主要資料表
        for model, table_name in tables:
            rows = session.query(model).all()
            for row in rows:
                columns = [c.name for c in model.__table__.columns]
                values = []
                for col in columns:
                    val = getattr(row, col)
                    if val is None:
                        values.append("NULL")
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    else:
                        # 處理字串轉義，避免單引號造成語法錯誤
                        safe_val = str(val).replace("'", "''")
                        values.append(f"'{safe_val}'")
                
                sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});"
                sql_statements.append(sql)
        
        # 2. 處理關聯表 (Many-to-Many)
        # item_sub_categories
        rel_results = session.execute(item_sub_categories.select()).all()
        for r in rel_results:
            sql_statements.append(f"INSERT INTO item_sub_categories (item_id, sub_category_id) VALUES ({r[0]}, {r[1]});")
            
        # item_tags
        rel_results = session.execute(item_tags.select()).all()
        for r in rel_results:
            sql_statements.append(f"INSERT INTO item_tags (item_id, tag_id) VALUES ({r[0]}, {r[1]});")
            
        return "\n".join(sql_statements)
    finally:
        session.close()

def get_all_data_json():
    """
    取得所有資料並轉換為適合 HTML/JSON 使用的結構。
    """
    session = db_session()
    try:
        categories = session.query(Category).all()
        sub_categories = session.query(SubCategory).all()
        tags = session.query(Tag).all()
        items = session.query(Item).all()

        return {
            "categories": [{"id": c.id, "user_id": c.user_id, "name": c.name} for c in categories],
            "sub_categories": [{"id": sc.id, "category_id": sc.category_id, "name": sc.name} for sc in sub_categories],
            "tags": [{"id": t.id, "user_id": t.user_id, "name": t.name} for t in tags],
            "items": [
                {
                    "id": i.id,
                    "user_id": i.user_id,
                    "category_id": i.category_id,
                    "category_name": i.category.name if i.category else None,
                    "title": i.title,
                    "description": i.description,
                    "place": i.place,
                    "done": i.done,
                    "completed_date": i.completed_date,
                    "sub_categories": [sc.name for sc in i.sub_categories],
                    "tags": [t.name for t in i.tags]
                } for i in items
            ]
        }
    finally:
        session.close()

def get_categories_summary(user_id=None):
    session = db_session()
    try:
        query = session.query(Category.name, func.count(case((Item.done == 0, 1)))) \
                       .outerjoin(Item, Item.category_id == Category.id)
        if user_id: query = query.filter(Category.user_id == user_id)
        results = query.group_by(Category.name).all()
        return [{"name": r[0], "count": r[1]} for r in results]
    finally: session.close()

def get_sub_categories_summary(user_id=None, category_name=None):
    session = db_session()
    try:
        query = session.query(Category.name, SubCategory.name, func.count(case((Item.done == 0, 1)))) \
                       .join(SubCategory, Category.id == SubCategory.category_id) \
                       .outerjoin(item_sub_categories, SubCategory.id == item_sub_categories.c.sub_category_id) \
                       .outerjoin(Item, Item.id == item_sub_categories.c.item_id)
        if user_id: query = query.filter(Category.user_id == user_id)
        if category_name: query = query.filter(Category.name == category_name)
        results = query.group_by(Category.name, SubCategory.name).all()
        
        # 結構化為 { "主分類": [{"name": "子類", "count": 1}, ...] }
        summary = {}
        for cat, sub, count in results:
            if cat not in summary: summary[cat] = []
            summary[cat].append({"name": sub, "count": count})
        return summary
    finally: session.close()

def get_tags_summary(user_id=None):
    session = db_session()
    try:
        query = session.query(Tag.name, func.count(case((Item.done == 0, 1)))) \
                       .outerjoin(item_tags, Tag.id == item_tags.c.tag_id) \
                       .outerjoin(Item, Item.id == item_tags.c.item_id)
        if user_id: query = query.filter(Tag.user_id == user_id)
        results = query.group_by(Tag.name).all()
        return [{"name": r[0], "count": r[1]} for r in results]
    finally: session.close()

def get_places_summary(user_id=None):
    session = db_session()
    try:
        query = session.query(Item.place, func.count(case((Item.done == 0, 1)))) \
                       .filter(Item.place != None)
        if user_id: query = query.filter(Item.user_id == user_id)
        results = query.group_by(Item.place).all()
        return [{"name": r[0], "count": r[1]} for r in results]
    finally: session.close()
