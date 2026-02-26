# LINE To-Do Bot

這是一個基於 Python Flask 開發的 LINE 聊天機器人，旨在幫助使用者高效管理待辦事項。除了基本的增刪查改功能外，還支援多筆快速新增、互動式編輯以及圖文選單。

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Flask Version](https://img.shields.io/badge/flask-3.1.2-green.svg)](https://flask.palletsprojects.com/)

---

## 🚀 主要功能 (Features)

- **使用者獨立資料**：利用 `user_id` 確保每位使用者的待辦清單完全獨立且安全。
- **分類管理**：支援「主分類」與「子分類」的二層式管理架構。
- **快速新增 (Quick Add)**：
  - 單筆：`主分類 + 子分類 + 名稱 [+ 地點]`
  - 多筆：`主分類 + 子分類 [+ 地點] ++ 項目1, 項目2, ...`
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

## 📦 安裝與設定 (Installation & Setup)

### 1. 複製專案
```bash
git clone <your-repo-url>
cd line-ToDo-bot
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

### 4. 環境變數設定
複製 `.env.sample` 並更名為 `.env`，填入以下必要資訊：
```env
LINE_CHANNEL_ACCESS_TOKEN="你的 Channel Access Token"
LINE_CHANNEL_SECRET="你的 Channel Secret"
NGROK_AUTHTOKEN="你的 ngrok Authtoken"

# 選填
PORT=5000
APP_ENV=development # production 則會嘗試連接 Postgres
DATABASE_URL="postgresql://user:pass@host:port/db" # 若 APP_ENV 為 production 則必填
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

### 📋 查詢 (List)
- `list`：列出所有待辦事項（按主分類分組）。
- `list <主分類>`：僅列出該分類的項目。
- `list <主分類>/<子分類>`：精確過濾。

### ➕ 新增 (Add)
- **單筆快捷**：`運動 + 健身房 + 深蹲 50下`
- **單筆帶地點**：`運動 + 健身房 + 深蹲 50下 + 台北健身院`
- **多筆快捷**：`追劇 + Netflix ++ 魷魚遊戲2, 星期三2, 怪奇物語5`
- **逐步引導**：直接輸入 `新增` 或 `add`，機器人會開始詢問細節。

### ⚙️ 管理 (Manage)
- **完成**：`完成 <編號>` (例如：`完成 12`)。支援多筆：`完成 12,13,15`。
- **編輯**：`編輯 <編號>`。機器人會詢問您要修改「名稱」還是「地點」。
- **刪除**：`刪除 <編號>`。支援多筆：`刪除 8,10`。

### 🛠️ 工具 (Utility)
- `help`：顯示指令說明。
- `contact`：顯示開發者聯絡資訊。
- `ping`：測試機器人回應。
- `/health` (Endpoint)：供 UptimeRobot 等工具監測服務狀態。

---

## 🗄️ 資料庫結構 (Database Schema)

專案採用關聯式設計：
- **`categories`**: `id`, `user_id`, `name`
- **`sub_categories`**: `id`, `category_id`, `name`
- **`items`**: `id`, `user_id`, `category_id`, `sub_category_id`, `title`, `place`, `done`, `completed_date`

詳情請參閱 [database_schema.md](./database_schema.md)。

---

## 📄 開源許可 (License)
本專案採用 [MIT License](LICENSE) 開源。
