# LINE To-Do Bot

# LINE To-Do Bot

這是一個基於 Python Flask 開發的 LINE 聊天機器人，旨在幫助使用者高效管理待辦事項。除了基本的增刪查改功能外，還支援多筆快速新增、互動式編輯以及圖文選單。

**✨ 本專案已全面升級為 LINE Flex Message 互動式清單！**

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask Version](https://img.shields.io/badge/flask-3.1.2-green.svg)](https://flask.palletsprojects.com/)

---

## 🚀 主要功能 (Features)

- **現代化 Flex Message 清單**：
  - **視覺化卡片**：待辦事項以精美的卡片 (Bubble) 形式呈現，並按分類自動分組。
  - **輪播導覽 (Carousel)**：支援左右滑動切換不同分類。
  - **一鍵操作**：每項待辦事項直接內建「完成」與「刪除」按鈕，無需手動輸入編號。
- **智慧型分頁系統**：
  - 自動處理大量分類，每頁顯示 9 個分類，並提供「下一頁」引導按鈕。
- **動態層次檢視**：
  - 總覽模式：以「主分類」作為卡片標題。
  - 分類檢視模式：以「子分類」作為卡片標題，資訊更集中。
- **分類與標籤管理**：
  - 支援「主分類」與「子分類」的二層式架構。
  - 自動提取名稱中的 `#標籤`。
- **快速新增 (Quick Add)**：
  - 單筆：`主分類 + 子分類1, 子分類2 + 名稱 #標籤 [+ 地點]`
  - 多筆：`主分類 + 子分類 [+ 地點] ++ 項目1 #標籤, 項目2 #標籤, ...`
- **互動對話 (Interactive Session)**：提供引導式對話流程來新增或編輯項目，並搭配 **Quick Reply** 減少打字。
- **圖文選單 (Rich Menu)**：底部常駐選單，一鍵呼叫「清單」、「說明」及「聯絡」。
- **靈活的資料庫支援**：
  - 開發環境：使用輕量級的 **SQLite**。
  - 生產環境：支援 **PostgreSQL** (Heroku/Render 友好)。

---

## 🛠️ 技術棧 (Tech Stack)

- **Backend**: Python 3.9+, Flask
- **Messaging**: LINE Messaging API (line-bot-sdk v3)
- **Database**: SQLite (Local), PostgreSQL (Production)
- **Tunneling**: pyngrok (用於本地開發接收 Webhook)
- **Environment**: python-dotenv

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

## 📦 安裝與設定 (Installation & Setup)

### 1. 設定環境變數

複製 `.env.sample` 並更名為 `.env`，填入以下必要資訊：

```env
NGROK_AUTHTOKEN="你的 ngrok Authtoken"
LINE_CHANNEL_ACCESS_TOKEN="你的 Channel Access Token"
LINE_CHANNEL_SECRET="你的 Channel Secret"
APP_ENV="development" # production 則會嘗試連接 Postgres
DATABASE_URL="postgresql://user:pass@host:port/db" # 若 APP_ENV 為 production 則必填
```

### 2. 建立虛擬環境

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. 安裝依賴

```bash
pip install -r requirements.txt
```

---

## 🏃 啟動與執行 (Running the App)

1. **啟動伺服器**：

   ```bash
   python app.py
   ```

   程式會自動啟動 `ngrok` 並顯示一個公開 URL（例如 `https://xxxx.ngrok-free.app`）。

2. **設定 Webhook**：
   前往 [LINE Developers Console](https://developers.line.biz/console/)，將 Webhook URL 設定為：
   `https://xxxx.ngrok-free.app/callback`

3. **設定圖文選單 (選填)**：
   確保目錄下有 `rich_menu.png` (2500x843)，然後執行：
   ```bash
   python setup_rich_menu.py
   ```

---

## 💬 指令說明 (Commands)

### 📋 查詢 (List) 與 導覽

- **總覽所有清單**：`list`
  - 以「主分類」分組，每張卡片代表一個主分類。
  - 若分類超過 10 個，會自動出現「下一頁」按鈕。

- **檢視特定主分類**：`list <主分類>`
  - 以「子分類」分組，每張卡片代表一個子分類。
  - 範例：`list 追劇清單`

- **檢視特定子分類**：`list <主分類>/<子分類>`
  - 僅列出該子分類下的所有項目。
  - 範例：`list 追劇清單/言情`

- **分頁跳轉**：`list [@位移量]`
  - 直接跳轉到指定的分類起始點。通常透過「下一頁」按鈕自動觸發。
  - 範例：`list @9` (從第 10 個分類開始顯示)

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

### 🛠️ 工具 (Utility)

- `help`：顯示指令說明。
- `contact`：顯示開發者聯絡資訊。
- `ping`：測試機器人回應。
- `/health` (Endpoint)：供 UptimeRobot 等工具監測服務狀態。
