# 試題2：RIS 3053 後端 API

## 目標

提供一個後端 API，讀取 `試題1/data/ris_doorplate.sqlite3`，讓使用者可以查詢爬蟲資料與爬蟲執行紀錄。

## 檔案說明

- `main.py`：HTTP API server 入口與路由。
- `repository.py`：SQLite 資料存取層。
- `config.json`：host、port、database path、分頁限制。
- `LINE_BY_LINE_EXPLANATION.md`：逐行程式碼說明文件。

## 執行方式

請先執行試題1爬蟲，產生：

```text
試題1/data/ris_doorplate.sqlite3
```

再啟動 API：

```powershell
cd C:\Users\user\ris_3053_gitlab_submission\試題2
python main.py
```

啟動成功會看到：

```text
RIS API service running at http://127.0.0.1:8000
Press Ctrl+C to stop.
```

## API 清單

### 健康檢查

```http
GET /health
```

PowerShell：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
```

### 查詢門牌資料

```http
GET /records
```

可用參數：

- `cityCode`
- `areaCode`
- `registerKind`
- `dateFrom`
- `dateTo`
- `q`
- `limit`
- `offset`

範例：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/records?cityCode=63000000&registerKind=1&limit=20"
```

### 查單筆資料

```http
GET /records/{id}
```

範例：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/records/1"
```

### 查爬蟲任務紀錄

```http
GET /jobs
```

範例：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/jobs?limit=10"
Invoke-RestMethod "http://127.0.0.1:8000/jobs?status=success"
```

## 異常狀態

如果 `/health` 回傳：

```json
"database_exists": false
```

代表尚未執行試題1爬蟲，或 `config.json` 的 `database_path` 指向錯誤。

## 與試題3 Log 與異常通知整合

API 每次查詢 `/records`、`/records/{id}`、`/jobs` 都會寫入查詢紀錄：

```text
logs/api-query.jsonl
```

異常通知規則：

- `/records` 查詢結果 `total = 0` 時，寫入 `../試題3/notifications/notifications.jsonl`。
- `/records/{id}` 查無資料時，寫入 `../試題3/notifications/notifications.jsonl`。
- 若設定 `NOTIFY_WEBHOOK_URL`，會同步 POST 通知 JSON 到 webhook。
