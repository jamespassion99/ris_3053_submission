# 試題1：RIS 3053 門牌資料爬蟲

## 題目目標

針對內政部戶政司網站 `https://www.ris.gov.tw/app/portal/3053`，透過「以編釘日期、編釘類別查詢」作為查詢條件，擷取門牌相關資料，並依序完成：

1. 原始查詢結果先落檔為 JSON。
2. 解析後另存 CSV。
3. 將結構化資料寫入 SQLite 資料庫。
4. 紀錄成功或失敗 log。
5. 可用內建排程定期執行。

## 查詢條件

設定檔：`conditions.json`

目前已依題目設定：

- 縣市：台北市 `63000000`
- 區域：台北市 12 區
- 編訂日期：民國 `114/09/01` 到 `114/11/30`
- 編訂類別：門牌初編 `registerKind = 1`

## 檔案說明

- `main.py`：爬蟲主程式、CLI 入口、一次執行與排程邏輯。
- `ris_client.py`：HTTP client，處理 Cookie、CSRF、CAPTCHA 下載、查詢 POST。
- `storage.py`：資料落檔、CSV 輸出、SQLite 建表與 upsert、log helper。
- `conditions.json`：查詢條件、輸出路徑、timeout、排程時間。
- `data/raw/`：每頁原始 JSON response。
- `data/csv/`：每頁解析後 CSV。
- `data/ris_doorplate.sqlite3`：SQLite 資料庫，執行後產生。
- `logs/`：執行過程 log 與 job JSONL。

## 執行方式

```powershell
cd C:\Users\user\ris_3053_gitlab_submission\試題1
python main.py --once
```

程式會下載 CAPTCHA 圖檔，畫面會顯示類似：

```text
請開啟 CAPTCHA 圖檔並輸入驗證碼：
...\data\captcha\captcha_xxx.png
CAPTCHA:
```

請立即開啟圖片，將看到的驗證碼輸入回 PowerShell。驗證碼可能會過期，請不要隔太久再輸入。

## 內建排程

`conditions.json` 可設定：

```json
"schedule": {
  "enabled": true,
  "daily_at": "02:00"
}
```

啟動排程：

```powershell
python main.py --schedule
```

## 輸出結果

成功查詢後會產生：

```text
data/raw/YYYY-MM-DD/city=.../area=.../kind=.../*.json
data/csv/YYYY-MM-DD/city=.../area=.../kind=.../*.csv
data/ris_doorplate.sqlite3
logs/crawler-info.log
logs/crawler-error.log
logs/crawler-job.jsonl
```

## 資料庫資料表

- `doorplate_record`：門牌資料。
- `crawl_job`：每個查詢任務與頁數的成功/失敗紀錄。

## 異常處理

- HTTP 失敗：`ris_client.py` 會回報 HTTP status 與部分 response body。
- 網站未回 JSON：會保留錯誤訊息並寫入失敗 job log。
- CAPTCHA 錯誤或過期：該 job 會失敗或回傳 0 筆，需要重新執行並快速輸入 CAPTCHA。
- 網站欄位變更：raw JSON 仍會先落檔，可依 raw 檔調整 `storage.py` 的解析邏輯後重跑匯入。

## 技術評估

本實作使用 Python 標準庫 `urllib.request`、`http.cookiejar`、`sqlite3`，未使用 Requests/Selenium/Scrapy，原因如下：

1. 目標查詢流程可透過 HTTP form POST 完成，不需要瀏覽器渲染。
2. 標準庫即可維持 Cookie、送出表單、下載 CAPTCHA、解析 JSON。
3. 不引入第三方套件，部署簡單，適合考題繳交與 Windows 環境執行。
4. CAPTCHA 採人工輸入，避免自動辨識或繞過驗證機制。

若未來網站改為大量 JavaScript 動態渲染，再評估改用 Selenium 或 Playwright。

## 與試題3異常通知整合

爬蟲在查詢頁初始化失敗、單頁查詢失敗、JSON 解析失敗、HTTP 失敗等異常時，會寫入：

```text
../試題3/notifications/notifications.jsonl
```

若環境變數 `NOTIFY_WEBHOOK_URL` 有設定，也會嘗試將同一筆通知以 JSON POST 到 webhook。Webhook 失敗不會中斷爬蟲主流程。
