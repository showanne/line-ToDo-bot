# 📈 Investment Module README

這個模組是「投資庫存狀態記錄機器人」的核心，主要用來幫使用者紀錄持股、更新現價、統計總投資表現，並以 LINE Flex Message 與 REST API 方式提供互動。

## 1. 模組定位

投資模組屬於本專案的子模組之一，目的如下：

- 記錄每個使用者的投資資產持有狀態
- 支援持股清單、資產總覽、損益統計
- 透過 LINE 指令快速新增、更新、刪除資產
- 對外提供 REST API，便於看板或其他服務整合

## 2. 主要功能

### 2.1 持股總覽

可快速查看：

- 投資總成本
- 市值
- 損益
- 損益率
- 各資產類別市值分布
- 持有資產數量

### 2.2 持股明細

可列出每一筆資產：

- `symbol`：標的代碼
- `name`：標的名稱
- `asset_type`：資產類別
- `quantity`：持有數量
- `cost_price`：成本單價
- `current_price`：現價
- `currency`：幣別
- `note`：備註

### 2.3 新增 / 更新 / 刪除

支援以下操作：

- `買入`：新增或累加持股
- `更新 <代碼> <現價>`：更新某標的現價
- `查看 <代碼>`：查看單一標的庫存明細
- `刪除投資 <ID>`：刪除指定資產

### 2.4 新增後的回饋

當使用者完成新增資產後，系統會立即返回該筆資產的單筆明細卡，而不是只回覆整體總覽。這張明細卡會顯示：

- 標的代號與名稱
- 持有數量
- 成本均價
- 現價
- 購買地點
- 市值與損益

## 3. LINE 指令說明

### 3.1 切換到投資模式

- `@投資`
- `切換模式:投資`
- `mode:investment`

### 3.2 基本命令

- `help` / `幫助`：顯示投資模組說明
- `ping`：檢查機器人是否正常運作
- `portfolio` / `總覽` / `投資總覽`：查看投資總覽
- `資產` / `持股` / `股票清單` / `明細`：查看持股明細
- `查看 <代碼>` / `明細 <代碼>`：查看單一標的庫存明細
- `買入` / `新增投資`：進入逐步新增流程

### 3.3 快速語法

#### 新增買入（簡化語法）

```text
投資 + 台股 + 2330 台積電 + 買入 1000 @ 600 於 玉山證券
```

> `於 玉山證券` 為可選的購買地點欄位，新增後會顯示在單筆明細中。

#### 逐步新增

```text
買入
```

後續會依序引導：

1. 輸入標的代碼與名稱
2. 輸入數量與單價，例如：`1000 @ 600 於 台北`

若你想補充購買地點，請在輸入格式中加入 `於 <地點>`。

#### 更新現價

```text
更新 2330 650
```

#### 查看單一檔股票明細

```text
查看 2330
```

#### 刪除資產

```text
刪除投資 1
```

## 4. REST API

### 4.1 投資總覽

- `GET /api/investment/summary`

Query Parameters：

- `user_id`：使用者 ID（預設為 `default_user`）

### 4.2 持股清單

- `GET /api/investment/assets`

Query Parameters：

- `user_id`：使用者 ID
- `type`：資產類別（可選）

### 4.3 新增資產

- `POST /api/investment/add`

Request Body：

```json
{
  "user_id": "test_user",
  "symbol": "2330",
  "name": "台積電",
  "asset_type": "台股",
  "quantity": 1000,
  "price": 600,
  "currency": "TWD",
  "purchase_place": "台北",
  "note": "長期持有"
}
```

### 4.4 更新現價

- `POST /api/investment/update-price`

Request Body：

```json
{
  "user_id": "test_user",
  "symbol": "2330",
  "current_price": 650
}
```

### 4.5 刪除資產

- `POST /api/investment/delete`

Request Body：

```json
{
  "user_id": "test_user",
  "id": 1
}
```

## 5. 核心資料模型

### `InvestmentAsset`

欄位說明：

- `user_id`：使用者識別
- `symbol`：資產代號
- `name`：資產名稱
- `asset_type`：類型（台股、美股、加密貨幣、基金、債券等）
- `quantity`：持有數量
- `cost_price`：平均成本單價
- `current_price`：目前市價
- `currency`：幣別
- `purchase_place`：購買地點
- `note`：備註

### `InvestmentTransaction`

紀錄資產交易歷史：

- `tx_type`：BUY / SELL / DIVIDEND
- `quantity`：交易數量
- `price`：成交價格
- `fee`：手續費
- `tx_date`：交易日期
- `note`：備註

## 6. 設計重點

- 基於 `add_or_update_asset()` 累加持倉與重新計算平均成本
- 以 `get_portfolio_summary()` 提供整體投資績效摘要
- 支援多使用者隔離，避免不同使用者資料互相汙染
- 若無資料時，總覽 API 會回傳空陣列而不是錯誤

## 7. 後續擴充建議

未來可以考慮加入：

- 資產分群圖表顯示
- 單一標的歷史價格追蹤
- 持倉警報與提醒
- `SELL` / `DIVIDEND` 交易紀錄補齊
- 與外部行情 API 整合
