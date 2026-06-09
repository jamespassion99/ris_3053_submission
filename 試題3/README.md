# 試題3：Log 收集器與異常通知平台

## 題目目標

建置 Log 收集器與異常通報平台，可檢視：

1. 試題1 爬蟲服務的即時 log。
2. 試題2 API 查詢紀錄。
3. 異常通知紀錄。

異常通知條件：

- 試題1：爬蟲過程發生異常時發送通知。
- 試題2：查詢資料為空時發送異常通知。

## 技術選擇

使用 Python 標準庫 `http.server` 建置簡易平台，不引入第三方套件。原因：

1. 符合考題展示需求，部署簡單。
2. 可直接讀取試題1/試題2產生的 log JSONL 檔。
3. Windows 環境可直接執行。
4. 未來若要正式化，可替換為 ELK、Grafana Loki、Prometheus Alertmanager 或 Slack/Teams webhook。

## 檔案說明

- `main.py`：Log collector HTTP 平台。
- `config.json`：平台 host/port 與各 log 檔案路徑。
- `notifications/notifications.jsonl`：試題1/試題2 寫入的通知紀錄，執行後產生。
- `執行說明.txt`：快速執行步驟。

## 執行方式

請先啟動或執行試題1、試題2，再啟動試題3：

```powershell
cd C:\Users\user\ris_3053_gitlab_submission\試題3
python main.py
```

啟動後開啟：

```text
http://127.0.0.1:9000
```

頁面每 10 秒自動刷新。

## JSON API

健康與摘要：

```powershell
Invoke-RestMethod "http://127.0.0.1:9000/api/summary"
```

讀取指定 log：

```powershell
Invoke-RestMethod "http://127.0.0.1:9000/api/logs?source=crawler_info"
Invoke-RestMethod "http://127.0.0.1:9000/api/logs?source=crawler_error"
Invoke-RestMethod "http://127.0.0.1:9000/api/logs?source=crawler_job"
Invoke-RestMethod "http://127.0.0.1:9000/api/logs?source=api_query"
Invoke-RestMethod "http://127.0.0.1:9000/api/logs?source=notifications"
```

## 通知格式

通知採 JSONL，每行一筆：

```json
{
  "created_at": "2026-06-09T00:00:00+00:00",
  "service": "試題1爬蟲",
  "severity": "error",
  "event_type": "crawler_page_failed",
  "message": "爬蟲分頁任務失敗",
  "details": {}
}
```

## Webhook 通知

若要外送通知，可設定環境變數：

```powershell
$env:NOTIFY_WEBHOOK_URL="https://example.com/webhook"
```

試題1/試題2 寫入通知時會同步 POST JSON 到該 webhook。Webhook 失敗不會中斷主流程。
