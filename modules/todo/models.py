# modules/todo/models.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, Table, Text, func, case
from sqlalchemy.orm import relationship
from core.database import Base, db_session, get_or_create

# --- 資料關聯表 ---

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

# --- 模型定義 ---

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
    sub_category_id = Column(Integer, ForeignKey('sub_categories.id', ondelete='SET NULL'), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    place = Column(String)
    done = Column(Integer, default=0)
    is_deleted = Column(Integer, default=0) # 0: 正常, 1: 已刪除
    completed_date = Column(String)
    category = relationship("Category", back_populates="items")
    sub_categories = relationship("SubCategory", secondary=item_sub_categories, backref="items")
    tags = relationship("Tag", secondary=item_tags, backref="items")

# --- 資料庫 CRUD API ---

def add_item(user_id, category_name, sub_category_names, title, tags=None, place=None):
    session = db_session()
    try:
        cat = get_or_create(session, Category, user_id=user_id, name=category_name)
        if isinstance(sub_category_names, str):
            sub_category_names = [s.strip() for s in sub_category_names.split(",") if s.strip()]
        sub_cats = [get_or_create(session, SubCategory, category_id=cat.id, name=sc) for sc in sub_category_names]
        tag_objs = [get_or_create(session, Tag, user_id=user_id, name=t) for t in (tags or [])]
        sub_cat_id = sub_cats[0].id if sub_cats else None
        new_item = Item(user_id=user_id, category_id=cat.id, sub_category_id=sub_cat_id, title=title, place=place, done=0, sub_categories=sub_cats, tags=tag_objs)
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

def mark_item_as_undone(user_id, item_ids):
    session = db_session()
    try:
        items = session.query(Item).filter(Item.id.in_(item_ids), Item.user_id == user_id, Item.is_deleted == 0).all()
        for i in items: i.done = 0; i.completed_date = None
        session.commit(); return len(items)
    except: session.rollback(); return 0
    finally: session.close()

def update_item(user_id, item_id, category_name, sub_category_names, title, tags=None, place=None, done=None):
    session = db_session()
    try:
        i = session.query(Item).filter(Item.id == item_id, Item.user_id == user_id).first()
        if not i: return False
        
        cat = get_or_create(session, Category, user_id=user_id, name=category_name)
        i.category_id = cat.id
        
        if isinstance(sub_category_names, str):
            sub_category_names = [s.strip() for s in sub_category_names.split(",") if s.strip()]
        sub_cats = [get_or_create(session, SubCategory, category_id=cat.id, name=sc) for sc in sub_category_names]
        i.sub_categories = sub_cats
        i.sub_category_id = sub_cats[0].id if sub_cats else None
        
        tag_objs = [get_or_create(session, Tag, user_id=user_id, name=t) for t in (tags or [])]
        i.tags = tag_objs
        
        i.title = title
        i.place = place
        if done is not None:
            i.done = int(done)
            if i.done == 1 and not i.completed_date:
                i.completed_date = datetime.now().isoformat()
            elif i.done == 0:
                i.completed_date = None
                
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

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
        results = session.query(
            Category.name,
            func.count(case(((Item.done == 0) & (Item.is_deleted == 0), 1)))
        ).outerjoin(Item, (Item.category_id == Category.id) & (Item.user_id == user_id)) \
         .filter(Category.user_id == user_id) \
         .group_by(Category.name).all()
        return results
    finally:
        session.close()

def list_sub_categories(user_id, category_name=None):
    session = db_session()
    try:
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
        return results
    finally:
        session.close()

def list_tags(user_id):
    session = db_session()
    try:
        results = session.query(
            Tag.name,
            func.count(case(((Item.done == 0) & (Item.is_deleted == 0), 1)))
        ).outerjoin(item_tags, Tag.id == item_tags.c.tag_id) \
         .outerjoin(Item, (Item.id == item_tags.c.item_id) & (Item.user_id == user_id)) \
         .filter(Tag.user_id == user_id) \
         .group_by(Tag.name).all()
        return results
    finally:
        session.close()

def list_places(user_id):
    session = db_session()
    try:
        results = session.query(
            Item.place,
            func.count(case(((Item.done == 0) & (Item.is_deleted == 0), 1)))
        ).filter(Item.user_id == user_id, Item.place != None) \
         .group_by(Item.place).all()
        return [r for r in results if r[0]]
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
    session = db_session()
    sql_statements = []
    tables = [
        (Category, "categories"),
        (SubCategory, "sub_categories"),
        (Tag, "tags"),
        (Item, "items")
    ]
    try:
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
                        safe_val = str(val).replace("'", "''")
                        values.append(f"'{safe_val}'")
                sql = f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(values)});"
                sql_statements.append(sql)
        rel_results = session.execute(item_sub_categories.select()).all()
        for r in rel_results:
            sql_statements.append(f"INSERT INTO item_sub_categories (item_id, sub_category_id) VALUES ({r[0]}, {r[1]});")
        rel_results = session.execute(item_tags.select()).all()
        for r in rel_results:
            sql_statements.append(f"INSERT INTO item_tags (item_id, tag_id) VALUES ({r[0]}, {r[1]});")
        return "\n".join(sql_statements)
    finally:
        session.close()

def get_all_data_json(user_id=None):
    session = db_session()
    try:
        if user_id:
            categories = session.query(Category).filter(Category.user_id == user_id).all()
            sub_categories = session.query(SubCategory).join(Category).filter(Category.user_id == user_id).all()
            tags = session.query(Tag).filter(Tag.user_id == user_id).all()
            items = session.query(Item).filter(Item.user_id == user_id).all()
        else:
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
                    "is_deleted": i.is_deleted,
                    "completed_date": i.completed_date,
                    "sub_categories": [sc.name for sc in i.sub_categories],
                    "tags": [t.name for t in i.tags]
                } for i in items
            ]
        }
    finally:
        session.close()

def get_all_users():
    session = db_session()
    try:
        user_ids = session.query(Item.user_id).distinct().all()
        uids = {u[0] for u in user_ids if u[0]}
        cat_user_ids = session.query(Category.user_id).distinct().all()
        for u in cat_user_ids:
            if u[0]:
                uids.add(u[0])
        return sorted(list(uids))
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
