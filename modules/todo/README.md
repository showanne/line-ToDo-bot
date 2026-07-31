# 📝 Todo Module README

這個模組是本專案的原生待辦事項管理核心，主要負責 LINE 對話式待辦輸入、分類管理、標籤與地點整理，以及強化版的 Flex Message 互動。

## 1. 模組定位

`todo` 模組提供：

- 待辦事項新增、完成、刪除、復原
- 主分類 / 子分類 / 標籤 / 地點管理
- 多筆快速新增語法
- 可瀏覽的 Flex Message 卡片與快速按鈕導覽
- 對外 REST API 供看板與其他服務查詢

## 2. 核心功能

### 2.1 待辦資料模型

模組透過 `db.add_item()`、`db.update_item()` 與 `db.list_items()` 等 CRUD 流程，管理每個使用者的待辦資料。

### 2.2 分類與標籤系統

支援：

- 主分類
- 子分類
- 標籤（`#`）
- 地點（`@`）

### 2.3 快速指令

常見範例：

```text
閱讀清單 + 耽美 + 銀翼獵手 #待買
追劇清單 + 言情 ++ 偷偷藏不住 @優酷, 難哄 @Netflix #必看
list
cat
subcat
help
```

## 3. 主要 API

- `GET /api/data`：取得指定使用者待辦資料
- `GET /api/users`：取得所有使用者
- `POST /api/items/add`：新增待辦事項
- `POST /api/items/edit`：編輯待辦事項
- `POST /api/items/delete`：刪除待辦事項
- `POST /api/items/restore`：復原待辦事項
- `POST /api/items/complete`：標記完成
- `POST /api/items/incomplete`：標記未完成

## 4. 設計重點

- 以分類路徑為導覽核心（例如 `主分類/子分類`）
- 讓使用者在 LINE 對話中即可完成 CRUD
- 使用 Flex Message 提升操作效率與互動體驗
- 將資料與視覺化看板、API 端點分層處理

## 5. 後續優化方向

- 新增更細的待辦優先級與提醒
- 與投資模組做跨模組分析（例如「工作與投資」混合視角）
- 擴充更多 LINE Quick Reply 情境
