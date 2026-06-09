# RIS 3053 試題繳交專案

本專案依題目要求用單一 GitLab 專案整理兩個試題資料夾：

- `試題1/`：內政部戶政司 3053 門牌資料爬蟲。
- `試題2/`：讀取試題 1 SQLite 資料庫的後端 API。

## 執行順序

1. 先執行 `試題1` 爬蟲，產生 raw JSON、CSV、SQLite 與 log。
2. 再執行 `試題2` API，透過 HTTP 查詢 SQLite 內的資料。

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
```

API 啟動後可測試：

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
Invoke-RestMethod "http://127.0.0.1:8000/records?limit=20"
Invoke-RestMethod "http://127.0.0.1:8000/jobs?limit=10"
```
