"""Main entry point for RIS 3053 doorplate crawler.

Usage examples:
  python main.py --once
  python main.py --conditions conditions.json --once
  python main.py --schedule          # uses schedule.daily_at in conditions.json

Notes:
  - Dates should use ROC format used by the website, e.g. 115/06/09.
  - CAPTCHA is operator-assisted. The program downloads an image and asks you to
    type the value. It does not bypass the verification mechanism.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

from ris_client import RisClient
from storage import (
    append_job_log,
    init_db,
    make_job_key,
    parse_records,
    record_job,
    save_csv,
    save_raw,
    setup_logging,
    upsert_records,
    utc_now,
)


def load_conditions(path: Path) -> Dict[str, Any]:
    """讀取爬蟲設定檔 conditions.json，回傳 Python dict。

    使用 utf-8-sig 是為了兼容 Windows 編輯器可能加上的 BOM，避免
    json.load 在檔案開頭遇到隱藏字元時失敗。
    """
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def run_once(config: Dict[str, Any], config_path: Path) -> int:
    """依照設定檔執行一次完整爬蟲流程。

    流程順序：
    1. 建立 log / raw / CSV / DB 路徑。
    2. 開啟查詢頁並取得 CSRF、CAPTCHA key。
    3. 下載 CAPTCHA 圖片，等待人工輸入。
    4. 逐頁查詢資料。
    5. 每頁先保存 raw JSON，再輸出 CSV，最後 upsert 到 SQLite。
    6. 每頁成功或失敗都寫入 crawl_job 與 logs。
    """
    # 所有相對路徑都以 conditions.json 所在資料夾為基準，方便整包搬移。
    base_dir = config_path.parent
    raw_dir = base_dir / config.get("raw_dir", "data/raw")
    csv_dir = base_dir / config.get("csv_dir", "data/csv")
    log_dir = base_dir / config.get("log_dir", "logs")
    db_path = base_dir / config.get("database_path", "data/ris_doorplate.sqlite3")
    captcha_dir = base_dir / "data" / "captcha"

    # 初始化共用資源：logger、SQLite 連線、HTTP client。
    logger = setup_logging(log_dir)
    conn = init_db(db_path)
    client = RisClient(config["base_url"], timeout=int(config.get("request_timeout_seconds", 30)))
    sleep_seconds = float(config.get("sleep_seconds_between_requests", 2))

    total_imported = 0
    queries: Iterable[Dict[str, Any]] = config.get("queries", [])
    for query in queries:
        # 每一個 query 對應 conditions.json 裡的一組縣市/行政區/日期/編釘類別。
        query_name = query.get("name", f"{query.get('cityCode')}-{query.get('areaCode')}")
        logger.info("Start query: %s", query_name)
        try:
            # RIS 查詢頁需要先走 main -> map -> query，才能取得有效 CSRF 與 captchaKey。
            query_page = client.open_query_page(query["cityCode"])

            # CAPTCHA 不做破解；只下載圖片並讓操作人員人工輸入。
            captcha_path = captcha_dir / f"captcha_{query_name}_{int(time.time())}.png"
            client.download_captcha(query_page.captcha_key, captcha_path)
            print("\n請開啟 CAPTCHA 圖檔並輸入驗證碼：")
            print(captcha_path.resolve())
            captcha_input = input("CAPTCHA: ").strip()
            if not captcha_input:
                raise RuntimeError("CAPTCHA is empty")

            # jqGrid API 以 page/rows 分頁；token 由前一頁 response 延續。
            page = 1
            token = None
            while True:
                started_at = utc_now()
                job_key = make_job_key(query, page)
                logger.info("Start job=%s", job_key)
                try:
                    # 送出「以編釘日期、編釘類別查詢」表單，取得一頁 JSON。
                    response = client.inquiry_date(
                        query=query,
                        csrf=query_page.csrf,
                        captcha_key=query_page.captcha_key,
                        captcha_input=captcha_input,
                        page=page,
                        rows=50,
                        token=token,
                    )

                    # 題目要求先落檔；因此 raw JSON 是第一個輸出，方便後續追查網站回應。
                    raw_path = save_raw(raw_dir, query, page, response)

                    # 將網站 response rows 清理為固定欄位，再輸出 CSV 與寫入 DB。
                    records = parse_records(response, query, raw_path)
                    csv_path = save_csv(csv_dir, query, page, records)
                    imported = upsert_records(conn, records)
                    total_imported += imported
                    finished_at = utc_now()

                    # SQLite job 表記錄每頁成功狀態，方便 API 或人工查詢。
                    record_job(
                        conn,
                        query,
                        page,
                        status="success",
                        raw_file_path=str(raw_path),
                        row_count=imported,
                        started_at=started_at,
                        finished_at=finished_at,
                    )

                    # JSONL log 方便未來接 ELK、Grafana Loki 或其他 log 監控工具。
                    append_job_log(
                        log_dir,
                        {
                            "job_key": job_key,
                            "status": "success",
                            "row_count": imported,
                            "raw_file": str(raw_path),
                            "csv_file": str(csv_path),
                            "started_at": started_at,
                            "finished_at": finished_at,
                        },
                    )
                    logger.info("Success job=%s rows=%s raw=%s csv=%s", job_key, imported, raw_path, csv_path)

                    # total 代表總頁數；查完最後一頁就跳出分頁迴圈。
                    token = response.get("token") or token
                    total_pages = int(response.get("total") or 1)
                    if page >= total_pages:
                        break
                    page += 1
                    time.sleep(sleep_seconds)
                except Exception as exc:
                    # 單頁失敗仍記錄 job 與 log，避免錯誤只出現在 console 而不可追蹤。
                    finished_at = utc_now()
                    record_job(
                        conn,
                        query,
                        page,
                        status="failed",
                        error_message=str(exc),
                        started_at=started_at,
                        finished_at=finished_at,
                    )
                    append_job_log(
                        log_dir,
                        {
                            "job_key": job_key,
                            "status": "failed",
                            "error": str(exc),
                            "started_at": started_at,
                            "finished_at": finished_at,
                        },
                    )
                    logger.exception("Failed job=%s", job_key)
                    break
        except Exception:
            # 例如 CSRF/CAPTCHA key 找不到時，尚未進入分頁，記在 query 層級 log。
            logger.exception("Query failed before paging: %s", query_name)
        finally:
            # 對政府網站保留間隔，避免短時間連續請求。
            time.sleep(sleep_seconds)

    logger.info("Crawler finished. imported_rows=%s db=%s", total_imported, db_path)
    conn.close()
    return total_imported


def run_scheduler(config_path: Path) -> None:
    """內建簡易每日排程器，依 conditions.json 的 schedule.daily_at 執行。

    這裡不用額外排程套件，改用常駐 while loop 每 30 秒檢查一次時間。
    若正式部署，也可以改由 Windows 工作排程器或 cron 呼叫 `python main.py --once`。
    """
    config = load_conditions(config_path)
    daily_at = config.get("schedule", {}).get("daily_at", "02:00")
    print(f"Scheduler started. Daily run time: {daily_at}. Press Ctrl+C to stop.")
    last_run_date = None
    while True:
        now = datetime.now()
        current_hm = now.strftime("%H:%M")
        # last_run_date 避免同一分鐘內重複觸發多次。
        if current_hm == daily_at and last_run_date != now.date():
            run_once(load_conditions(config_path), config_path)
            last_run_date = now.date()
        time.sleep(30)


def parse_args() -> argparse.Namespace:
    """解析命令列參數，支援指定設定檔、單次執行與排程執行。"""
    parser = argparse.ArgumentParser(description="RIS 3053 doorplate crawler")
    parser.add_argument("--conditions", default="conditions.json", help="Path to conditions JSON")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--schedule", action="store_true", help="Run built-in daily scheduler")
    return parser.parse_args()


def main() -> int:
    """CLI 主入口，確認設定檔存在後決定要跑一次或進入排程模式。"""
    args = parse_args()
    config_path = Path(args.conditions).resolve()
    if not config_path.exists():
        print(f"Conditions file not found: {config_path}", file=sys.stderr)
        return 2

    if args.schedule:
        run_scheduler(config_path)
        return 0

    # Default behavior is one run, so double-click / plain `python main.py` works.
    config = load_conditions(config_path)
    run_once(config, config_path)
    return 0


if __name__ == "__main__":
    # SystemExit 會把 main() 回傳值變成系統 exit code，方便批次檔或排程器判斷成功/失敗。
    raise SystemExit(main())
