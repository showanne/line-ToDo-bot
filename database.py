import os
import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime

# This file implements a switcher to use a PostgreSQL database in production
# (if DATABASE_URL is set) and a local SQLite database for development.

class SqliteEngine:
    def __init__(self, db_file="todo.db"):
        self.db_file = db_file
        print("Using SQLite database for local development.")

    def _connect(self):
        return sqlite3.connect(self.db_file)

    def init_db(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, name TEXT NOT NULL
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS sub_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL, name TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, category_id INTEGER NOT NULL,
                sub_category_id INTEGER NOT NULL, title TEXT NOT NULL, desc TEXT, place TEXT,
                done INTEGER DEFAULT 0, completed_date TEXT,
                FOREIGN KEY(category_id) REFERENCES categories(id),
                FOREIGN KEY(sub_category_id) REFERENCES sub_categories(id)
            )""")
        conn.commit()
        conn.close()

    def get_category_id(self, user_id, name):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT id FROM categories WHERE user_id=? AND name=?", (user_id, name))
        row = c.fetchone()
        if row:
            cid = row[0]
        else:
            c.execute("INSERT INTO categories (user_id, name) VALUES (?, ?)", (user_id, name))
            cid = c.lastrowid
            conn.commit()
        conn.close()
        return cid

    def get_sub_category_id(self, category_id, name):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT id FROM sub_categories WHERE category_id=? AND name=?", (category_id, name))
        row = c.fetchone()
        if row:
            sid = row[0]
        else:
            c.execute("INSERT INTO sub_categories (category_id, name) VALUES (?, ?)", (category_id, name))
            sid = c.lastrowid
            conn.commit()
        conn.close()
        return sid

    def add_item(self, user_id, category, sub_category, title, desc="", done=0, place=None):
        cid = self.get_category_id(user_id, category)
        sid = self.get_sub_category_id(cid, sub_category)
        completed_date = datetime.now().isoformat() if done else None
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            INSERT INTO items (user_id, category_id, sub_category_id, title, desc, place, done, completed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, cid, sid, title, desc, place, done, completed_date))
        conn.commit()
        conn.close()

    def delete_item(self, user_id, item_ids):
        conn = self._connect()
        c = conn.cursor()
        deleted_count = 0
        for item_id in item_ids:
            c.execute("SELECT id FROM items WHERE id=? AND user_id=?", (item_id, user_id))
            if c.fetchone():
                c.execute("DELETE FROM items WHERE id=?", (item_id,))
                deleted_count += 1
        conn.commit()
        conn.close()
        return deleted_count

    def mark_item_as_done(self, user_id, item_ids):
        conn = self._connect()
        c = conn.cursor()
        updated_count = 0
        for item_id in item_ids:
            c.execute("SELECT id FROM items WHERE id=? AND user_id=?", (item_id, user_id))
            if c.fetchone():
                c.execute("UPDATE items SET done=1, completed_date=? WHERE id=?", (datetime.now().isoformat(), item_id))
                updated_count += 1
        conn.commit()
        conn.close()
        return updated_count

    def get_item(self, user_id, item_id):
        conn = self._connect()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT i.id, i.title, i.place, c.name as category_name, sc.name as sub_category_name
            FROM items i JOIN categories c ON i.category_id = c.id JOIN sub_categories sc ON i.sub_category_id = sc.id
            WHERE i.id=? AND i.user_id=?
        """, (item_id, user_id))
        item = c.fetchone()
        conn.close()
        return item

    def edit_item(self, user_id, item_id, field, value):
        if field not in ['title', 'place']: return False
        conn = self._connect()
        c = conn.cursor()
        query = f"UPDATE items SET {field}=? WHERE id=? AND user_id=?"
        c.execute(query, (value, item_id, user_id))
        updated_rows = c.rowcount
        conn.commit()
        conn.close()
        return updated_rows > 0

    def list_items(self, user_id, category=None):
        conn = self._connect()
        c = conn.cursor()
        query = """
            SELECT i.id, i.title, i.desc, i.done, i.place, i.completed_date, c.name, sc.name
            FROM items i JOIN categories c ON i.category_id = c.id JOIN sub_categories sc ON i.sub_category_id = sc.id
            WHERE i.user_id=?
        """
        params = [user_id]
        if category:
            query += " AND c.name=?"
            params.append(category)
        query += " ORDER BY c.name, i.id"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return rows


class PostgresEngine:
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL")
        print("Using PostgreSQL database for production.")

    def _connect(self):
        return psycopg2.connect(self.db_url)

    def init_db(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS sub_categories (
                id SERIAL PRIMARY KEY, category_id INTEGER NOT NULL, name TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, category_id INTEGER NOT NULL,
                sub_category_id INTEGER NOT NULL, title TEXT NOT NULL, desc TEXT, place TEXT,
                done INTEGER DEFAULT 0, completed_date TEXT,
                FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE,
                FOREIGN KEY(sub_category_id) REFERENCES sub_categories(id) ON DELETE CASCADE
            )""")
        conn.commit()
        conn.close()

    def get_category_id(self, user_id, name):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT id FROM categories WHERE user_id=%s AND name=%s", (user_id, name))
        row = c.fetchone()
        if row:
            cid = row[0]
        else:
            c.execute("INSERT INTO categories (user_id, name) VALUES (%s, %s) RETURNING id", (user_id, name))
            cid = c.fetchone()[0]
            conn.commit()
        conn.close()
        return cid

    def get_sub_category_id(self, category_id, name):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT id FROM sub_categories WHERE category_id=%s AND name=%s", (category_id, name))
        row = c.fetchone()
        if row:
            sid = row[0]
        else:
            c.execute("INSERT INTO sub_categories (category_id, name) VALUES (%s, %s) RETURNING id", (category_id, name))
            sid = c.fetchone()[0]
            conn.commit()
        conn.close()
        return sid

    def add_item(self, user_id, category, sub_category, title, desc="", done=0, place=None):
        cid = self.get_category_id(user_id, category)
        sid = self.get_sub_category_id(cid, sub_category)
        completed_date = datetime.now().isoformat() if done else None
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            INSERT INTO items (user_id, category_id, sub_category_id, title, desc, place, done, completed_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, cid, sid, title, desc, place, done, completed_date))
        conn.commit()
        conn.close()

    def delete_item(self, user_id, item_ids):
        conn = self._connect()
        c = conn.cursor()
        deleted_count = 0
        for item_id in item_ids:
            c.execute("SELECT id FROM items WHERE id=%s AND user_id=%s", (item_id, user_id))
            if c.fetchone():
                c.execute("DELETE FROM items WHERE id=%s", (item_id,))
                deleted_count += 1
        conn.commit()
        conn.close()
        return deleted_count

    def mark_item_as_done(self, user_id, item_ids):
        conn = self._connect()
        c = conn.cursor()
        updated_count = 0
        for item_id in item_ids:
            c.execute("SELECT id FROM items WHERE id=%s AND user_id=%s", (item_id, user_id))
            if c.fetchone():
                c.execute("UPDATE items SET done=1, completed_date=%s WHERE id=%s", (datetime.now().isoformat(), item_id))
                updated_count += 1
        conn.commit()
        conn.close()
        return updated_count

    def get_item(self, user_id, item_id):
        conn = self._connect()
        c = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        c.execute("""
            SELECT i.id, i.title, i.place, c.name as category_name, sc.name as sub_category_name
            FROM items i JOIN categories c ON i.category_id = c.id JOIN sub_categories sc ON i.sub_category_id = sc.id
            WHERE i.id=%s AND i.user_id=%s
        """, (item_id, user_id))
        item = c.fetchone()
        conn.close()
        return item

    def edit_item(self, user_id, item_id, field, value):
        if field not in ['title', 'place']: return False
        conn = self._connect()
        c = conn.cursor()
        query = f"UPDATE items SET {field}=%s WHERE id=%s AND user_id=%s"
        c.execute(query, (value, item_id, user_id))
        updated_rows = c.rowcount
        conn.commit()
        conn.close()
        return updated_rows > 0

    def list_items(self, user_id, category=None):
        conn = self._connect()
        c = conn.cursor()
        query = """
            SELECT i.id, i.title, i.desc, i.done, i.place, i.completed_date, c.name, sc.name
            FROM items i JOIN categories c ON i.category_id = c.id JOIN sub_categories sc ON i.sub_category_id = sc.id
            WHERE i.user_id=%s
        """
        params = [user_id]
        if category:
            query += " AND c.name=%s"
            params.append(category)
        query += " ORDER BY c.name, i.id"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return rows


# --- DB Manager ---
# This will decide which database engine to use based on environment variables.
if os.getenv("DATABASE_URL"):
    db_engine = PostgresEngine()
else:
    db_engine = SqliteEngine()

# --- Public API ---
# Expose the engine's methods to the rest of the application.
init_db = db_engine.init_db
get_category_id = db_engine.get_category_id
get_sub_category_id = db_engine.get_sub_category_id
add_item = db_engine.add_item
delete_item = db_engine.delete_item
mark_item_as_done = db_engine.mark_item_as_done
get_item = db_engine.get_item
edit_item = db_engine.edit_item
list_items = db_engine.list_items
