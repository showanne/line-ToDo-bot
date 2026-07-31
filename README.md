# LINE To-Do Bot

這是一個基於 Python Flask 開發的高進階 LINE 聊天機器人，旨在提供最直覺、美觀的待辦事項管理體驗。本專案整合了 LINE Flex Message 技術與智慧指令解析，將複雜的任務與類別管理簡化為指尖的點擊操作。

**✨ 本次升級：看板互動式 CRUD 與多使用者管理重磅上線！**
- 數據看板解鎖完整編輯與新增能力（彈窗新增/編輯、標記完成/未完成、軟刪除與復原）。
- 支援多使用者切換（User Switcher），輕鬆檢視及管理不同 LINE 使用者的待辦事項。
- 開放標準 RESTful REST API，提供端點進行待辦事項的增刪改查。

---

## 🚀 主要功能 (Features)

### 1. 智慧型快捷按鈕系統 (Context-Aware Quick Replies)

系統現在會根據您當下的操作情境，在鍵盤上方自動彈出最相關的快捷選項：
- **新增完項目後**：自動提供 `📜列出項目` (查看該分類)、`➕繼續新增` (預填同分類) 及 `📁主分類`。
- **瀏覽清單時**：
    - **查看子分類清單**：提供 `➕新增至此`、`⬅️回主分類`。
    - **查看標籤/地點時**：提供 `🏷️標籤清單` 或 `📍地點清單` 的快速切換。
- **管理介面中**：在 `cat` 或 `subcat` 指令後，提供 `➕新增主分類` 等管理捷徑。

### 2. Flex Message 詳情卡片優化

針對新增或查詢出的事項詳情卡片，進行了深度排版優化：
- **新增「✏️ 編輯」功能**：卡片內建編輯按鈕，發現輸入錯誤可立即修正，無需輸入複雜指令。
- **階層化按鈕佈局**：
    - **✅ 標記完成**：醒目的實心按鈕，佔據首位。
    - **✏️ 編輯 / 🗑️ 刪除**：採用橫向並排設計，節省空間且視覺平衡。
- **視覺引導**：所有按鈕皆配有直觀 Emoji 圖示，提升操作直覺度。

### 3. 「3-9-1」法則與 2x2 智慧導覽矩陣

為了確保極致的閱讀體驗與系統穩定性，本專案所有清單均遵循「3-9-1」排版法則，並配備了全新的 **2x2 智慧導覽列**：

- **3-9-1 規則**：每張卡片顯示 3 個項目，每輪最多 9 張卡片，第 10 張自動轉化為帶有提示的「下一頁」按鈕。
- **2x2 智慧導覽矩陣**：所有卡片底部現在採用 2x2 四格按鈕佈局，針對 8 種不同情境動態調整：
  - **清單導覽**：提供 `⬅️ 上一層`、`🔍 探索 (Help)`、`➕ 精準新增` 與 `📜 列表排序`。
  - **操作回饋 (成功/刪除)**：提供 `⬅️ 返回清單`、`➕ 再新增` 與 `📜 查看清單`。
  - **搜尋與管理**：針對標籤、地點、分類管理提供專屬的操作捷徑。
- **精準路徑新增 (Precision Add)**：
  - 在檢視詳細清單或剛完成操作時，導覽列的 `➕` 按鈕會自動帶入當前的「主分類/子分類」完整路徑，實現「指尖即所得」的連續輸入體驗。
- **實時待辦計數**：所有列表名稱旁皆顯示**未完成事項數量**（例如：`工作 (5)`），讓任務負荷量一目了然。
- **資訊密度優化**：
  - **標籤與地點**：採用**雙欄位緊湊佈局**，大幅減少捲動次數。
  - **分組合併導覽**：`subcat` 指令會將同一主分類的子類合併顯示。
  - **自動拆分序號**：若內容眾多，系統會自動拆分並標註序號（例如：`工作 (1/3)`）。
- **全功能按鈕**：不論主、子分類，皆具備 **「摘要查看、重新命名、預填新增」** 三大互動功能。

### 3. 視覺化互動幫助系統

- **Carousel 輪播選單**：`help` 指令採用美觀的卡片分組（基本操作、查詢管理、快捷語法），配有直觀圖示與功能說明。
- **指令預填技術 (Interactive Prefill)**：點擊幫助卡片中的指令，系統會**自動開啟手機鍵盤**並**預填指令範本**（如 `完成 `、`編輯 `、`#`），使用者只需補上參數即可送出，大幅降低記憶負擔。
- **智慧路徑預填**：點擊類別卡片的 **[新增]** 按鈕，系統會自動代入路徑，跳過引導步驟，直接詢問「事項名稱」。

### 4. 視覺化狀態回饋與軟刪除系統 (Visual Feedback & Soft Delete)

為了提供最直覺且安全的管理體驗，系統導入了 **Soft Delete (軟刪除)** 機制與全方位的 Carousel 回饋：

- **標題背景色規範 (Color Scheme)**：
  - **🟩 綠色 (`#27AE60`)**：**新增成功** 或 **復原成功**。
  - **🟧 橘色 (`#E67E22`)**：**尚未完成**。用於顯示待處理事項或編輯後的狀態。
  - **🟦 藍色 (`#3498DB`)**：**標記完成**。執行 `完成 <ID>` 後的回饋。
  - **🟥 紅色 (`#E74C3C`)**：**事項已刪除 / 操作失敗**。
- **防止誤刪的復原機制**：
  - 執行 `刪除 <ID>` 後，系統會回傳紅色的「🗑️ 事項已刪除」卡片。
  - **復原按鈕**：刪除確認卡片中附帶綠色的 `[復原事項]` 按鈕，點擊即可瞬間找回資料。
  - **復原指令**：亦可手動輸入 `復原 <ID>` (如：`復原 5, 8`) 來批次恢復項目。
- **自動化相容性處理**：系統啟動時會自動檢查資料庫結構，若為舊版本升級，將自動補齊 `is_deleted` 欄位，確保服務不中斷。

### 5. 數據看板 (Visualization Dashboard)

- **現代化 Web 介面**：提供 `/dashboard` 專屬網頁，採用響應式賽博朋克風格卡片設計，適合在大螢幕上管理任務。
- **多使用者切換 (User Switcher)**：頂部選單可切換檢視特定 LINE User ID 或檢視全域事項。
- **互動式 CRUD 彈窗**：點擊「新增單位」或卡片上的「編輯」按鈕，可直接透過視窗修改標題、主分類、子分類、標籤、地點與完成狀態。
- **列內快速操作 (Inline Actions)**：事項表格右側提供一鍵完成/取消完成、編輯彈窗開啟、刪除與一鍵復原按鈕。
- **維度導覽側邊欄**：左側自動彙總所有主分類、標籤與地點，並即時顯示未完成事項的數量與篩選狀態。
- **動態過濾與自動同步**：點擊側邊欄即可即時過濾事項；看板具備 30 秒自動刷新機制，確保網頁與 LINE Bot 資料無縫同步。

---

## � 模組文件

- [modules/todo/README.md](modules/todo/README.md)：待辦模組說明、指令、API 與設計重點。
- [modules/investment/README.md](modules/investment/README.md)：投資庫存狀態記錄模組說明、指令、API 與資料模型。

## �🛠️ 技術 (Tech Stack)

- **Backend**: Python 3.9+, Flask
- **Messaging**: LINE Messaging API (line-bot-sdk v3)
- **Database**: SQLite (Local), PostgreSQL (Production), Alembic (自動檢查並更新資料庫結構)
- **ORM**: SQLAlchemy (支援資料庫層級的對話狀態持久化)
- **Tunneling**: pyngrok (用於本地開發接收 Webhook)
- **UI Framework**: LINE Flex Message (JSON-based modern UI)

---

## 資料庫與遷移 (Database & Migrations)

本專案使用 SQLAlchemy 作為 ORM，並導入 **Alembic** 進行資料庫版本管理。這確保了開發與生產環境的資料庫結構始終保持一致。

### 核心資料表：

- **`categories`**: `id`, `user_id`, `name`
- **`sub_categories`**: `id`, `category_id`, `name`
- **`tags`**: `id`, `user_id`, `name`
- **`items`**: `id`, `user_id`, `category_id`, `sub_category_id`, `title`, `description`, `place`, `done`, `is_deleted`, `completed_date`
- **`item_sub_categories`**: `item_id`, `sub_category_id` (多對多)
- **`item_tags`**: `item_id`, `tag_id` (多對多)

詳情請參閱 [database_schema.md](./database_schema.md)。

### 如何進行結構變更：

當您修改了 `database.py` 中的模型（例如新增欄位）時，請執行以下步驟：

1. **產生遷移腳本**：
   ```bash
   alembic revision --autogenerate -m "描述變更內容"
   ```
2. **自動更新**：
   部屬後，程式會在啟動時透過 `db.init_db()` 自動執行 `alembic upgrade head`，您不需要手動操作資料庫。

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
- **標籤管理**：`tags`
  - 列出所有已使用的 **#標籤**，點擊標籤可直接搜尋相關事項。
  - 範例：`list #待播` (針對特定標籤列出清單)
- **地點管理**：`places`
  - 列出所有已記錄的 **@地點**，點擊可直接搜尋在該地點的事項。
  - 範例：`list @愛奇藝` (針對特定地點列出清單)
- **快捷搜尋**：
  - 直接輸入 `#標籤名` (例：`#緊急`) 或 `@地點名` (例：`@全聯`) 即可快速列出匹配項目。

### ➕ 新增 (Add)

本系統已全面標準化地點與標籤輸入，統一使用 `@` 與 `#` 符號：

- **單筆快捷新增**：`主分類 + 子分類1 [, 子分類2 ] + 事項 [@地點] [#標籤]`
  - 範例 1：`閱讀清單 + 耽美 + 銀翼獵手 #待買`
  - 範例 2：`追劇清單 + 奇幻 + 西出玉門 @騰訊視頻`
  - 範例 3：`追劇清單 + 競技, 奇幻 + 穿越火線 @騰訊視頻 #待播`
  - 範例 4：`追劇清單 + 競技 + 英雄聯盟電競劇 #待確認`

- **多筆快捷新增**：`主分類 + 子分類 ++ 事項1 [@地點] [#標籤], 事項2 [@地點] [#標籤]`
  - 範例 1：`追劇清單 + 言情 ++ 偷偷藏不住 @優酷, 難哄 @Netflix #必看`
  - 範例 2：`追劇清單 + 競技, 言情 ++ 愛情而已 @騰訊視頻, 在暴雪時分 @騰訊視頻`
  - 範例 3：`主分類 + 子分類 ++ 項目1 @地點, 項目2 #標籤`

- **逐步對話新增**：輸入 `新增`
  - 機器人會引導輸入主分類與子分類。
  - 在輸入「事項內容」時，直接寫入 `@地點` 或 `#標籤` 即可完成新增。

### ⚙️ 管理 (Manage)

- `完成 <編號>` / `刪除 <編號>` / `復原 <編號>`
  - 支援多筆操作（半形逗號隔開）。
  - 編號可透過 `list` 指令查詢。
  - 範例：`完成 12, 13`、`刪除 8`、`復原 8`
- `編輯 <編號>`
  - 修改事項名稱或地點。
- **重新命名**：
  - 主分類：`rename_cat 舊名稱 -> 新名稱`
  - 子分類：`rename_sub 主分類/舊名 -> 新名`

### 🛠️ 工具 (Utility)

- `help`：顯示指令說明。
- `contact`：顯示開發者聯絡資訊。
- `ping`：測試機器人回應。

---

## 🧪 API 端點與數據看板

### 📊 視覺化看板 (Dashboard)

- **URL**: `GET /dashboard`
- **說明**: 進入現代化 Web 看板，即時查看分類統計與事項卡片。

### 📡 RESTful API 與 JSON 資料端點

- **使用者清單**: `GET /api/users` - 取得系統中所有有記錄的 `user_id` 列表。
- **所有資料**: `GET /api/data` - 回傳結構化的 JSON（支援 `?user_id=xxx` 參數進行使用者過濾）。
- **事項 CRUD 操作 API**:
  - `POST /api/items/add` - 新增待辦事項 (`user_id`, `title`, `category`, `sub_categories`, `tags`, `place`)。
  - `POST /api/items/edit` - 編輯待辦事項 (`id`, `user_id`, `title`, `category`, `sub_categories`, `tags`, `place`, `done`)。
  - `POST /api/items/delete` - 軟刪除指定 ID 事項 (`user_id`, `ids`)。
  - `POST /api/items/restore` - 復原指定 ID 事項 (`user_id`, `ids`)。
  - `POST /api/items/complete` - 批次標記事項為已完成 (`user_id`, `ids`)。
  - `POST /api/items/incomplete` - 批次標記事項為未完成 (`user_id`, `ids`)。
- **維度統計 API**:
  - `GET /api/categories` - 主分類統計清單。
  - `GET /api/sub-categories` - 子分類統計清單 (可帶 `?category=xxx` 過濾)。
  - `GET /api/tags` - 標籤統計清單。
  - `GET /api/places` - 地點統計清單。
  - _以上維度端點皆支援 `?user_id=xxx` 參數來查詢特定使用者。_

### 💾 資料匯出與工具

- **SQL 匯出**: `GET /api/export` - 將資料庫轉換為 SQL `INSERT` 語句。
- **健康檢查**: `GET /health` - 供 UptimeRobot 等工具監測。

---
