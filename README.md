# RIS 3053 試題繳交專案

本專案依題目要求用單一 GitLab 專案整理兩個試題資料夾：

- `試題1/`：內政部戶政司 3053 門牌資料爬蟲。
- `試題2/`：讀取試題 1 SQLite 資料庫的後端 API。
- `試題3/`：Log 收集器與異常通知平台。
- `試題4/`：上述題目的系統架構圖與資料流圖。

## 執行順序

1. 先執行 `試題1` 爬蟲，產生 raw JSON、CSV、SQLite 與 log。
2. 再執行 `試題2` API，透過 HTTP 查詢 SQLite 內的資料。
3. 最後執行 `試題3` 平台，檢視試題1即時 log、試題2 API 查詢紀錄與異常通知。

## 環境

- Python 3.10+
- 未使用第三方套件，皆使用 Python 標準庫。
- CAPTCHA 採人工輸入，不繞過網站驗證機制。

## 快速指令

```powershell
cd 試題1
python main.py --once

cd ..\試題2
python main.py

cd ..\試題3
python main.py
```

API 啟動後可測試：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
Invoke-RestMethod "http://127.0.0.1:8000/records?limit=20"
Invoke-RestMethod "http://127.0.0.1:8000/jobs?limit=10"
```

## 試題3平台

啟動後開啟：

```powershell
cd 試題3
python main.py
```

瀏覽：`http://127.0.0.1:9000`。

通知規則：

- 試題1爬蟲過程發生異常時，寫入 `試題3/notifications/notifications.jsonl`。
- 試題2 `/records` 查詢結果為空或 `/records/{id}` 查無資料時，寫入異常通知。
- 試題2 API 查詢紀錄寫入 `試題2/logs/api-query.jsonl`。

## 試題4系統架構圖

架構圖文件：

```text
試題4/系統架構圖.md
```

內容包含整體系統架構、資料流、部署流程、異常通知流程，使用 Mermaid 語法，可在 GitHub / GitLab Markdown 直接檢視。
