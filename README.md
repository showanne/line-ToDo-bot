# LINE To-Do Bot

這是一個基於 Python Flask 開發的高進階 LINE 聊天機器人，旨在提供最直覺、美觀的待辦事項管理體驗。本專案整合了 LINE Flex Message 技術與智慧指令解析，將複雜的任務與類別管理簡化為指尖的點擊操作。

**✨ 本次升級：類別管理系統全面導入 3-9-1 智慧分頁！**

---

## 🚀 主要功能 (Features)

### 1. 「3-9-1」全方位排版法則

為了確保極致的閱讀體驗與系統穩定性，本專案所有清單（待辦、分類）均遵循此法則：

- **3 (Items)**：每張卡片固定顯示 **3 個項目**（事項或子分類）。
- **9 (Cards)**：每輪輪播最多展示 **9 張資料卡片**。
- **1 (Next Page)**：第 10 張卡片自動轉化為帶有範圍提示的 **「下一頁」** 按鈕。

### 2. 層次化類別管理系統

- **分組合併導覽**：`subcat` 指令會將同一主分類的子類合併顯示，並具備強烈的歸屬感設計。
- **自動拆分序號**：若子分類眾多，系統會自動拆分並標註序號（例如：`工作 (1/3)`），讓導覽更清晰。
- **全功能按鈕**：不論主、子分類，皆具備 **「摘要查看、重新命名、預填新增」** 三大互動功能。

### 3. 高效預填新增流程

- **智慧路徑預填**：點擊類別卡片的 **[新增]** 按鈕，系統會自動代入路徑，跳過引導步驟，直接詢問「事項名稱」，大幅提升效率。

---

## 🛠️ 技術 (Tech Stack)

- **Backend**: Python 3.9+, Flask
- **Messaging**: LINE Messaging API (line-bot-sdk v3)
- **Database**: SQLite (Local), PostgreSQL (Production)
- **ORM**: SQLAlchemy (支援資料庫層級的對話狀態持久化)
- **Tunneling**: pyngrok (用於本地開發接收 Webhook)
- **UI Framework**: LINE Flex Message (JSON-based modern UI)

---

## 資料庫

### 專案採用關聯式設計：

- **`categories`**: `id`, `user_id`, `name`
- **`sub_categories`**: `id`, `category_id`, `name`
- **`tags`**: `id`, `user_id`, `name`
- **`items`**: `id`, `user_id`, `category_id`, `title`, `place`, `done`, `completed_date`
- **`item_sub_categories`**: `item_id`, `sub_category_id` (多對多)
- **`item_tags`**: `item_id`, `tag_id` (多對多)

詳情請參閱 [database_schema.md](./database_schema.md)。

### 專案的資料庫 (`todo.db`) 主要包含以下資料表：

1.  **`categories`**: 儲存使用者建立的主分類。
    - `id`: 主鍵
    - `user_id`: LINE 使用者 ID
    - `name`: 分類名稱

2.  **`sub_categories`**: 儲存子分類，並關聯到主分類。
    - `id`: 主鍵
    - `category_id`: 關聯到 `categories` 表的 ID
    - `name`: 子分類名稱

3.  **`items`**: 儲存待辦事項的詳細內容。
    - `id`: 主鍵
    - `user_id`: LINE 使用者 ID
    - `category_id`: 關聯到 `categories` 表的 ID
    - `sub_category_id`: 關聯到 `sub_categories` 表的 ID
    - `title`: 待辦事項標題
    - `desc`: 描述（目前版本尚未使用）
    - `place`: 地點
    - `done`: 完成狀態 (0: 未完成, 1: 已完成)
    - `completed_date`: 完成日期

---

## 📦 安裝與啟動

1.  **設定環境**：
    複製 `.env.sample` 並填入 LINE API 金鑰。

    ```env
    NGROK_AUTHTOKEN="你的 ngrok Authtoken"
    LINE_CHANNEL_ACCESS_TOKEN="你的 Channel Access Token"
    LINE_CHANNEL_SECRET="你的 Channel Secret"
    APP_ENV="development" # production 則會嘗試連接 Postgres
    DATABASE_URL="postgresql://user:pass@host:port/db" # 若 APP_ENV 為 production 則必填
    ```

2.  **建立虛擬環境**

    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **安裝依賴**

    ```bash
    pip install -r requirements.txt
    ```

4.  **執行專案**：

    ```bash
    python app.py
    ```

    程式會自動啟動 `ngrok` 並顯示一個公開 URL（例如 `https://xxxx.ngrok-free.app`）。

5.  **設定 Webhook**：
    前往 [LINE Developers Console](https://developers.line.biz/console/)，將 Webhook URL 設定為：
    `https://xxxx.ngrok-free.app/callback`

6.  **設定圖文選單 (選填)**：
    確保目錄下有 `rich_menu.png` (2500x843)，然後執行：

    ```bash
    python setup_rich_menu.py
    ```

---

## 💬 指令說明 (Commands)

### 📋 查詢 (List) 與 類別管理

- **所有待辦摘要**：`list`
  - 以「主分類」分組，每張卡片代表一個主分類，顯示該分類最新的 3 個項目。
- **管理主分類**：`categories` 或 `cat`
  - 列出主分類卡片，提供摘要、更名、新增的功能按鈕。
- **管理子分類**：`sub_categories` 或 `sub_categories <主分類>` 或 `subcat`
  - 依主分類分組顯示，每 3 個子類一張卡片，提供摘要、更名、新增的功能按鈕。
  - 支援過濾：`sub_categories <主分類>` 僅列出該主分類下的子分類。
- **分類摘要**：`list <主分類>`
  - 以「子分類」分組，每張卡片顯示該子分類最新的 3 個項目。
  - 範例：`list 追劇清單`
- **詳細清單**：`list <主分類>/<子分類>`
  - 進入「完整模式」，按每 3 個項目一卡片，完整列出所有內容。
  - 範例：`list 追劇清單/言情`
- **翻頁導覽**：`list [@位移量]` / `categories [@位移量]` / `subcat [@位移量]` (通常由按鈕自動觸發)。
  - 直接跳轉至特定卡片起始點（通常由「下一頁」按鈕自動觸發）。
  - 範例：`list 追劇清單/競技 @9` (從第 10 個分類開始顯示)

### ➕ 新增 (Add)

- **單筆快捷新增**：`主分類 + 子分類1 [, 子分類2 ] + 事項 [#標籤] [+ 地點]`
  - 使用 `+` 符號快速新增一筆待辦事項。地點、標籤為選填。
  - 範例 1：`閱讀清單 + 耽美 + 銀翼獵手`
  - 範例 2：`追劇清單 + 奇幻 + 西出玉門 + 騰訊視頻`
  - 範例 3：`追劇清單 + 競技, 奇幻 + 騰訊視頻 + 穿越火線`
  - 範例 4：`追劇清單 + 競技 + 英雄聯盟電競劇 #待確認`

- **多筆快捷新增**：`主分類 + 子分類 [, 子分類2 ] [+ 地點] + 事項1 [#標籤], 事項2 [#標籤]`
  - 使用 `++` 符號串聯同主分類、子分類、地點的待辦事項。地點、標籤為選填。
  - 範例 1：`追劇清單 + 言情 + 優酷 ++ 偷偷藏不住, 難哄`
  - 範例 2：`追劇清單 + 競技, 言情 + 騰訊視頻 ++ 愛情而已, 在暴雪時分`
  - 範例 3：`主分類 + 子分類 + 地點 ++ 項目1 #標籤, 項目2 #標籤`

- **逐步新增**：`新增`
  - 輸入「新增」後，機器人會透過對話一步步引導您輸入主分類、子分類、名稱和地點，完成新增。
  - 過程中可點選 Quick Reply 按鈕「取消」或將地點設為「無」。

### ⚙️ 管理 (Manage)

- `完成 <編號>`
  - 將指定編號的待辦事項標示為「已完成」。
  - 編號可透過 `list` 指令查詢。
  - 範例：`完成 12`

- `編輯 <編號>`
  - 啟動對話模式，修改指定編號的待辦事項。
  - 提供 Quick Reply 按鈕，方便快速選擇「名稱」或「地點」進行修改，也可選擇「取消」。
  - 範例：`編輯 15`

- `刪除 <編號>`
  - 永久刪除指定編號的待辦事項。
  - 範例：`刪除 8`

- **重新命名主分類**：`rename_cat 舊名稱 -> 新名稱`
  - 將現有的主分類更名。支援包含空格的名稱。
  - 範例：`rename_cat 工作 事項 -> 極重要事項`

- **重新命名子分類**：`rename_sub 主分類/舊子名 -> 新子名`
  - 將特定主分類下的子分類更名。支援包含空格的名稱。
  - 範例：`rename_sub 工作 專案 / 企劃 草案 -> 最終企劃`

### 🛠️ 工具 (Utility)

- `help`：顯示指令說明。
- `contact`：顯示開發者聯絡資訊。
- `ping`：測試機器人回應。
- `/health` (Endpoint)：供 UptimeRobot 等工具監測服務狀態。
