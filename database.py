import sqlite3

def init_db():
    """
    初始化資料庫，如果資料表不存在，則建立它們。
    """
    conn = sqlite3.connect('todo_bot.db')
    cursor = conn.cursor()

    # 建立主分類表 (main_categories)
    # user_id 欄位用來識別不同 LINE 使用者的資料
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS main_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        name TEXT NOT NULL,
        UNIQUE(user_id, name)
    )
    ''')

    # 建立子分類表 (sub_categories)
    # main_category_id 是用來關聯到主分類的外鍵
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sub_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        main_category_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        FOREIGN KEY (main_category_id) REFERENCES main_categories (id),
        UNIQUE(main_category_id, name)
    )
    ''')

    # 建立清單項目表 (items)
    # sub_category_id 是用來關聯到子分類的外鍵
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sub_category_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        is_completed BOOLEAN NOT NULL DEFAULT 0,
        create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_date TIMESTAMP,
        place_type TEXT,
        place_name TEXT,
        FOREIGN KEY (sub_category_id) REFERENCES sub_categories (id)
    )
    ''')

    conn.commit()
    conn.close()
    print("資料庫 'todo_bot.db' 已檢查並成功初始化。")

if __name__ == '__main__':
    # 如果直接執行這個 python 檔案，就會初始化資料庫
    init_db()