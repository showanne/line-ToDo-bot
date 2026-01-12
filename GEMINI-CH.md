# GEMINI.md

## 專案概述 (Project Overview)

本專案是一個 **LINE 待辦事項機器人 (LINE To-Do Bot)**，這是一個在 LINE 通訊平台上運作的聊天機器人，旨在幫助使用者管理其待辦清單。本專案使用 **Python** 與 **Flask** 網頁框架建置。使用者可以透過聊天指令來新增、列出、編輯及刪除待辦事項。每位使用者的待辦清單皆為獨立儲存。

此應用程式使用 **SQLite** 資料庫來儲存資料。在開發環境中，則使用 `ngrok` 將本地的 Flask 伺服器暴露於網際網路，以便接收來自 LINE 平台的 Webhook。

### 主要技術棧 (Main Technologies)

- **後端 (Backend):** Python, Flask
- **資料庫 (Database):** SQLite
- **LINE 整合:** line-bot-sdk-python
- **開發環境隧道 (Tunneling):** pyngrok

## 構建與執行 (Building and Running)

### 1. 設定環境

首先，請建立虛擬環境並安裝必要的依賴套件。

```bash
# 建立虛擬環境
python -m venv venv

# 啟用虛擬環境
# Windows 系統
venv\Scripts\activate
# macOS/Linux 系統
source venv/bin/activate

# 安裝依賴套件
pip install -r requirements.txt

```

### 2. 設定環境變數

將 `.env.sample` 檔案複製並重新命名為 `.env`，並填入必要的憑證資訊。

```bash
cp .env.sample .env

```

您需要在 `.env` 檔案中填入您的 LINE Channel Access Token、LINE Channel Secret 以及 ngrok Authtoken。

```text
LINE_CHANNEL_ACCESS_TOKEN="您的_LINE_CHANNEL_ACCESS_TOKEN"
LINE_CHANNEL_SECRET="您的_LINE_CHANNEL_SECRET"
NGROK_AUTHTOKEN="您的_NGROK_AUTHTOKEN"

```

### 3. 執行應用程式

使用以下指令啟動 Flask 應用程式：

```bash
python app.py

```

應用程式啟動後，`ngrok` 會為您的本地伺服器產生一個公網 URL。您需要將此 URL 設定到 LINE Developer Console 的 Webhook 設定中。該 URL 會在應用程式啟動時顯示在終端機（Console）中。

## 開發規範 (Development Conventions)

- **狀態管理 (State Management):** 應用程式使用一個簡單的記憶體字典 (`user_states`) 來管理多步驟指令（如「新增」或「編輯」）的對話狀態。
- **資料庫 (Database):** 資料庫直接在 `app.py` 中進行初始化與管理。若資料庫檔案不存在，則會自動建立 Schema（資料表結構）。所有資料庫操作均由同一檔案內的輔助函式（helper functions）處理。
- **指令處理 (Commands):** 使用者指令在主要的 `/callback` Webhook 端點進行處理。程式碼會檢查特定的關鍵字與指令模式以觸發不同動作。簡單指令會直接處理，而複雜的多步驟指令則會利用狀態管理字典來追蹤進度。
- **依賴管理 (Dependencies):** 專案的依賴套件清單列於 `requirements.txt` 中。
