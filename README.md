# 專案簡介：LINE To-Do Bot

這是一個使用 Python 和 Flask 框架開發的 LINE 聊天機器人，旨在提供一個方便的待辦事項（To-Do List）管理工具。使用者可以透過 LINE 聊天室與機器人互動，輕鬆新增、查詢待辦項目。

## 主要功能

- **使用者獨立資料**：每個 LINE 使用者的待辦清單都是獨立的，資料會與其 `user_id` 綁定。
- **分類管理**：支援主分類與子分類，讓使用者可以更好地組織待辦事項。
- **快捷新增**：透過簡單的 `+` 符號指令，可以快速新增待辦事項，甚至標示地點與完成狀態。
- **清單查詢**：可以查詢所有或特定分類下的待辦事項。

## 技術棧

- **後端框架**: [Flask](https://flask.palletsprojects.com/) - 一個輕量級的 Python Web 框架，用於接收 LINE Webhook 請求。
- **程式語言**: [Python](https://www.python.org/)
- **LINE 整合**: [line-bot-sdk-python](https://github.com/line/line-bot-sdk-python) - 用於處理 LINE Messaging API 的官方 SDK。
- **資料庫**: [SQLite](https://www.sqlite.org/index.html) - 一個輕量級的檔案型資料庫，透過 Python 內建的 `sqlite3` 函式庫進行操作。
- **開發環境**:
  - [ngrok](https://ngrok.com/) (`pyngrok`) - 用於在開發階段建立安全的網路通道，將本機的 Web 服務暴露給公網，方便接收 LINE 的 Webhook 事件。
  - [python-dotenv](https://github.com/theskumar/python-dotenv) - 用於管理專案中的環境變數，如 API 金鑰和設定。

## 資料庫結構

專案的資料庫 (`todo.db`) 主要包含以下資料表：

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

## 如何使用

1.  **設定環境變數**:
    複製 `.env.sample` 並重新命名為 `.env`，填入你的 LINE Channel Access Token、Channel Secret 和 ngrok Authtoken。

2.  **安裝依賴**:

    ```bash
    pip install -r requirements.txt
    ```

3.  **啟動應用程式**:

    ```bash
    python app.py
    ```

    啟動後，`ngrok` 會產生一個公開的 URL，請將該 URL + `/callback` 設定到你的 LINE Developer Console 的 Webhook URL。

## 指令說明

您可以透過以下指令與 To-Do Bot 互動：

### 查詢與檢視

-   `list`
    -   列出您所有的待辦事項。
    -   清單會依照「主分類」進行分組，並按項目編號排序。
    -   範例：`list`

-   `list <主分類>`
    -   僅列出指定主分類下的待辦事項。
    -   範例：`list 追劇清單`

-   `help`
    -   顯示所有可用指令的說明。

### 新增待辦事項

-   **快捷新增**：`主分類 + 子分類 + 名稱 [+ 地點]`
    -   使用 `+` 符號快速新增一筆待辦事項。地點為選填。
    -   範例 1：`閱讀清單 + 科幻 + 三體`
    -   範例 2：`追劇清單 + 奇幻 + 西出玉門 + 騰訊視頻`

-   **逐步新增**：`新增`
    -   輸入「新增」後，機器人會透過對話一步步引導您輸入主分類、子分類、名稱和地點，完成新增。

### 管理待辦事項

-   `完成 <編號>`
    -   將指定編號的待辦事項標示為「已完成」。
    -   編號可透過 `list` 指令查詢。
    -   範例：`完成 12`

-   `編輯 <編號>`
    -   啟動對話模式，修改指定編號的待辦事項。
    -   您可以選擇修改「名稱」或「地點」。
    -   範例：`編輯 15`

-   `刪除 <編號>`
    -   永久刪除指定編號的待辦事項。
    -   範例：`刪除 8`
