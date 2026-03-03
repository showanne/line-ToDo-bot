# database.py
import os
import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime

# 本檔案實作了資料庫切換機制：
# 在開發環境使用 SQLite (本地檔案)，在生產環境 (若有 DATABASE_URL) 則切換至 PostgreSQL。

class SqliteEngine:
    """SQLite 資料庫引擎，用於本地開發環境。"""
    def __init__(self, db_file="todo.db"):
        self.db_file = db_file
        print("Using SQLite database for local development.")

    def _connect(self):
        """建立 SQLite 連線。"""
        return sqlite3.connect(self.db_file)

    def init_db(self):
        """初始化資料表，並處理 SQLite 的欄位遷移。"""
        conn = self._connect()
        c = conn.cursor()

        # 1. 建立基本分類表與子分類表
        c.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, name TEXT NOT NULL
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS sub_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER NOT NULL, name TEXT NOT NULL,
                FOREIGN KEY(category_id) REFERENCES categories(id)
            )""")

        # 2. 檢查 items 表是否需要遷移 (SQLite 不支援直接修改欄位屬性，因此若舊版 sub_category_id 為 NOT NULL 則需手動遷移)
        c.execute("PRAGMA table_info(items)")
        columns = c.fetchall()

        needs_migration = False
        if columns:
            # 檢查舊版的 sub_category_id 是否為 NOT NULL
            sub_cat_col = next((col for col in columns if col[1] == 'sub_category_id'), None)
            if sub_cat_col and sub_cat_col[3] == 1: # 1 代表 NOT NULL
                needs_migration = True
        else:
            # 資料表不存在，直接建立新版結構
            c.execute("""
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, category_id INTEGER NOT NULL,
                    sub_category_id INTEGER, title TEXT NOT NULL, description TEXT, place TEXT,
                    done INTEGER DEFAULT 0, completed_date TEXT,
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )""")

        # 3. 建立多對多關聯表 (Bridge Tables) 與 標籤表
        c.execute("""
            CREATE TABLE IF NOT EXISTS item_sub_categories (
                item_id INTEGER NOT NULL, sub_category_id INTEGER NOT NULL,
                PRIMARY KEY (item_id, sub_category_id),
                FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
                FOREIGN KEY(sub_category_id) REFERENCES sub_categories(id) ON DELETE CASCADE
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, name TEXT NOT NULL
            )""")
        c.execute("""
            CREATE TABLE IF NOT EXISTS item_tags (
                item_id INTEGER NOT NULL, tag_id INTEGER NOT NULL,
                PRIMARY KEY (item_id, tag_id),
                FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
                FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )""")

        # 4. 執行 SQLite 遷移：將單一子分類欄位轉換為多對多關聯表存儲
        if needs_migration:
            print("Migrating SQLite schema to support multiple sub-categories...")
            # a. 將舊資料移至關聯表
            c.execute("INSERT OR IGNORE INTO item_sub_categories (item_id, sub_category_id) SELECT id, sub_category_id FROM items")

            # b. 重建 items 表以移除 sub_category_id 的 NOT NULL 限制
            c.execute("ALTER TABLE items RENAME TO items_old")
            c.execute("""
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, category_id INTEGER NOT NULL,
                    sub_category_id INTEGER, title TEXT NOT NULL, description TEXT, place TEXT,
                    done INTEGER DEFAULT 0, completed_date TEXT,
                    FOREIGN KEY(category_id) REFERENCES categories(id)
                )""")
            c.execute("""
                INSERT INTO items (id, user_id, category_id, title, description, place, done, completed_date)
                SELECT id, user_id, category_id, title, description, place, done, completed_date FROM items_old
            """)
            c.execute("DROP TABLE items_old")
            print("Migration completed.")

        conn.commit()
        conn.close()

    def get_category_id(self, user_id, name):
        """取得主分類 ID，若不存在則為該使用者自動建立一個。"""
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
        """取得子分類 ID，若不存在則在該主分類下建立。"""
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

    def get_tag_id(self, user_id, name):
        """取得標籤 ID，若不存在則建立。"""
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT id FROM tags WHERE user_id=? AND name=?", (user_id, name))
        row = c.fetchone()
        if row:
            tid = row[0]
        else:
            c.execute("INSERT INTO tags (user_id, name) VALUES (?, ?)", (user_id, name))
            tid = c.lastrowid
            conn.commit()
        conn.close()
        return tid

    def add_item(self, user_id, category, sub_categories, title, tags=None, description="", done=0, place=None):
        """新增一筆待辦事項，支援多個子分類與標籤。"""
        cid = self.get_category_id(user_id, category)

        # 處理子分類列表 (可以是字串或清單)
        if isinstance(sub_categories, str):
            sub_categories = [s.strip() for s in sub_categories.split(",") if s.strip()]

        sub_ids = [self.get_sub_category_id(cid, sc) for sc in sub_categories]
        tag_ids = [self.get_tag_id(user_id, t) for t in (tags or [])]

        completed_date = datetime.now().isoformat() if done else None
        conn = self._connect()
        c = conn.cursor()
        # 插入項目主表
        c.execute("""
            INSERT INTO items (user_id, category_id, title, description, place, done, completed_date)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, cid, title, description, place, done, completed_date))
        item_id = c.lastrowid

        # 插入子分類與標籤的關聯資料
        for sid in sub_ids:
            c.execute("INSERT INTO item_sub_categories (item_id, sub_category_id) VALUES (?, ?)", (item_id, sid))
        for tid in tag_ids:
            c.execute("INSERT INTO item_tags (item_id, tag_id) VALUES (?, ?)", (item_id, tid))

        conn.commit()
        conn.close()

    def delete_item(self, user_id, item_ids):
        """刪除指定的一筆或多筆待辦事項。"""
        conn = self._connect()
        c = conn.cursor()
        deleted_count = 0
        for item_id in item_ids:
            c.execute("SELECT id FROM items WHERE id=? AND user_id=?", (item_id, user_id))
            if c.fetchone():
                c.execute("DELETE FROM item_sub_categories WHERE item_id=?", (item_id,))
                c.execute("DELETE FROM item_tags WHERE item_id=?", (item_id,))
                c.execute("DELETE FROM items WHERE id=?", (item_id,))
                deleted_count += 1
        conn.commit()
        conn.close()
        return deleted_count

    def mark_item_as_done(self, user_id, item_ids):
        """將指定的一筆或多筆待辦事項標記為完成。"""
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
        """獲取單一項目的詳細資訊。"""
        conn = self._connect()
        conn.row_factory = sqlite3.Row # 使其可透過欄位名稱存取
        c = conn.cursor()
        c.execute("""
            SELECT i.id, i.title, i.place, c.name as category_name,
                   (SELECT GROUP_CONCAT(sc.name, ', ')
                    FROM item_sub_categories isc
                    JOIN sub_categories sc ON isc.sub_category_id = sc.id
                    WHERE isc.item_id = i.id) as sub_category_names,
                   (SELECT GROUP_CONCAT(t.name, ', #')
                    FROM item_tags it
                    JOIN tags t ON it.tag_id = t.id
                    WHERE it.item_id = i.id) as tag_names
            FROM items i
            JOIN categories c ON i.category_id = c.id
            WHERE i.id=? AND i.user_id=?
        """, (item_id, user_id))
        item = c.fetchone()
        conn.close()
        return item

    def edit_item(self, user_id, item_id, field, value):
        """編輯待辦事項的指定欄位 (目前支援 title 與 place)。"""
        if field not in ['title', 'place']: return False
        conn = self._connect()
        c = conn.cursor()
        query = f"UPDATE items SET {field}=? WHERE id=? AND user_id=?"
        c.execute(query, (value, item_id, user_id))
        updated_rows = c.rowcount
        conn.commit()
        conn.close()
        return updated_rows > 0

    def list_items(self, user_id, category=None, sub_category=None):
        """列出使用者的待辦清單，可選主分類與子分類篩選。"""
        conn = self._connect()
        c = conn.cursor()
        query = """
            SELECT i.id, i.title, i.description, i.done, i.place, i.completed_date, c.name,
                   (SELECT GROUP_CONCAT(sc.name, ', ')
                    FROM item_sub_categories isc
                    JOIN sub_categories sc ON isc.sub_category_id = sc.id
                    WHERE isc.item_id = i.id) as sub_categories,
                   (SELECT GROUP_CONCAT(t.name, ', #')
                    FROM item_tags it
                    JOIN tags t ON it.tag_id = t.id
                    WHERE it.item_id = i.id) as tags
            FROM items i
            JOIN categories c ON i.category_id = c.id
            WHERE i.user_id=?
        """
        params = [user_id]
        if category:
            query += " AND c.name=?"
            params.append(category)

        if sub_category:
            query += """ AND i.id IN (
                SELECT isc.item_id FROM item_sub_categories isc
                JOIN sub_categories sc ON isc.sub_category_id = sc.id
                WHERE sc.name=?
            )"""
            params.append(sub_category)

        query += " ORDER BY c.name, i.id"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return rows


class PostgresEngine:
    """PostgreSQL 資料庫引擎，用於生產環境。"""
    def __init__(self):
        url = os.getenv("DATABASE_URL")
        # 處理 Heroku 等平台提供的 postgres:// 格式
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        self.db_url = url
        print("Using PostgreSQL database for production.")

    def _connect(self):
        """建立 PostgreSQL 連線。"""
        try:
            return psycopg2.connect(self.db_url)
        except Exception as e:
            # 隱藏密碼的日誌輸出
            display_url = self.db_url
            if self.db_url and "@" in self.db_url:
                prefix = self.db_url.split("@")[0].split(":")[0]
                suffix = self.db_url.split("@")[-1]
                display_url = f"{prefix}://****@{suffix}"
            print(f"PostgreSQL 連線失敗！")
            print(f"使用的 URL 格式: {display_url}")
            print(f"錯誤訊息: {e}")
            raise e

    def init_db(self):
        """初始化 PostgreSQL 資料表與遷移邏輯。"""
        conn = self._connect()
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS categories (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL)")
        c.execute("CREATE TABLE IF NOT EXISTS sub_categories (id SERIAL PRIMARY KEY, category_id INTEGER NOT NULL, name TEXT NOT NULL, FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE)")

        # 檢查舊版欄位是否存在
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='items' AND column_name='sub_category_id'")
        has_old_col = c.fetchone()

        if not has_old_col:
            c.execute("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, category_id INTEGER NOT NULL,
                    title TEXT NOT NULL, description TEXT, place TEXT,
                    done INTEGER DEFAULT 0, completed_date TEXT,
                    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE CASCADE
                )""")

        c.execute("""
            CREATE TABLE IF NOT EXISTS item_sub_categories (
                item_id INTEGER NOT NULL, sub_category_id INTEGER NOT NULL,
                PRIMARY KEY (item_id, sub_category_id),
                FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
                FOREIGN KEY(sub_category_id) REFERENCES sub_categories(id) ON DELETE CASCADE
            )""")
        c.execute("CREATE TABLE IF NOT EXISTS tags (id SERIAL PRIMARY KEY, user_id TEXT NOT NULL, name TEXT NOT NULL)")
        c.execute("""
            CREATE TABLE IF NOT EXISTS item_tags (
                item_id INTEGER NOT NULL, tag_id INTEGER NOT NULL,
                PRIMARY KEY (item_id, tag_id),
                FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE,
                FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
            )""")

        # 若有舊欄位，將資料遷移到多對多關聯表並解除舊欄位的 NOT NULL 限制
        if has_old_col:
            c.execute("INSERT INTO item_sub_categories (item_id, sub_category_id) SELECT id, sub_category_id FROM items WHERE sub_category_id IS NOT NULL ON CONFLICT DO NOTHING")
            c.execute("ALTER TABLE items ALTER COLUMN sub_category_id DROP NOT NULL")
            c.execute("UPDATE items SET sub_category_id = NULL")

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

    def get_tag_id(self, user_id, name):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT id FROM tags WHERE user_id=%s AND name=%s", (user_id, name))
        row = c.fetchone()
        if row:
            tid = row[0]
        else:
            c.execute("INSERT INTO tags (user_id, name) VALUES (%s, %s) RETURNING id", (user_id, name))
            tid = c.fetchone()[0]
            conn.commit()
        conn.close()
        return tid

    def add_item(self, user_id, category, sub_categories, title, tags=None, description="", done=0, place=None):
        cid = self.get_category_id(user_id, category)
        if isinstance(sub_categories, str):
            sub_categories = [s.strip() for s in sub_categories.split(",") if s.strip()]
        sub_ids = [self.get_sub_category_id(cid, sc) for sc in sub_categories]
        tag_ids = [self.get_tag_id(user_id, t) for t in (tags or [])]
        completed_date = datetime.now().isoformat() if done else None
        conn = self._connect()
        c = conn.cursor()
        c.execute("""
            INSERT INTO items (user_id, category_id, title, description, place, done, completed_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (user_id, cid, title, description, place, done, completed_date))
        item_id = c.fetchone()[0]
        for sid in sub_ids:
            c.execute("INSERT INTO item_sub_categories (item_id, sub_category_id) VALUES (%s, %s)", (item_id, sid))
        for tid in tag_ids:
            c.execute("INSERT INTO item_tags (item_id, tag_id) VALUES (%s, %s)", (item_id, tid))
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
            SELECT i.id, i.title, i.place, c.name as category_name,
                   (SELECT STRING_AGG(sc.name, ', ')
                    FROM item_sub_categories isc
                    JOIN sub_categories sc ON isc.sub_category_id = sc.id
                    WHERE isc.item_id = i.id) as sub_category_names,
                   (SELECT STRING_AGG(t.name, ', #')
                    FROM item_tags it
                    JOIN tags t ON it.tag_id = t.id
                    WHERE it.item_id = i.id) as tag_names
            FROM items i JOIN categories c ON i.category_id = c.id
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

    def list_items(self, user_id, category=None, sub_category=None):
        conn = self._connect()
        c = conn.cursor()
        query = """
            SELECT i.id, i.title, i.description, i.done, i.place, i.completed_date, c.name,
                   (SELECT STRING_AGG(sc.name, ', ')
                    FROM item_sub_categories isc
                    JOIN sub_categories sc ON isc.sub_category_id = sc.id
                    WHERE isc.item_id = i.id) as sub_categories,
                   (SELECT STRING_AGG(t.name, ', #')
                    FROM item_tags it
                    JOIN tags t ON it.tag_id = t.id
                    WHERE it.item_id = i.id) as tags
            FROM items i JOIN categories c ON i.category_id = c.id
            WHERE i.user_id=%s
        """
        params = [user_id]
        if category:
            query += " AND c.name=%s"
            params.append(category)
        if sub_category:
            query += " AND i.id IN (SELECT isc.item_id FROM item_sub_categories isc JOIN sub_categories sc ON isc.sub_category_id = sc.id WHERE sc.name=%s)"
            params.append(sub_category)
        query += " ORDER BY c.name, i.id"
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return rows


# --- 資料庫引擎自動切換與對外介面實作 ---
app_env = os.getenv("APP_ENV", "development").lower()
database_url = os.getenv("DATABASE_URL")

# 根據環境變數決定使用哪種資料庫引擎
if app_env == "production" and database_url:
    db_engine = PostgresEngine()
else:
    db_engine = SqliteEngine()

# 統一對外公開的 API 介面，隱藏後端資料庫引擎的差異
init_db = db_engine.init_db
get_category_id = db_engine.get_category_id
get_sub_category_id = db_engine.get_sub_category_id
get_tag_id = db_engine.get_tag_id
add_item = db_engine.add_item
delete_item = db_engine.delete_item
mark_item_as_done = db_engine.mark_item_as_done
get_item = db_engine.get_item
edit_item = db_engine.edit_item
list_items = db_engine.list_items
