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
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def run_once(config: Dict[str, Any], config_path: Path) -> int:
    base_dir = config_path.parent
    raw_dir = base_dir / config.get("raw_dir", "data/raw")
    csv_dir = base_dir / config.get("csv_dir", "data/csv")
    log_dir = base_dir / config.get("log_dir", "logs")
    db_path = base_dir / config.get("database_path", "data/ris_doorplate.sqlite3")
    captcha_dir = base_dir / "data" / "captcha"

    logger = setup_logging(log_dir)
    conn = init_db(db_path)
    client = RisClient(config["base_url"], timeout=int(config.get("request_timeout_seconds", 30)))
    sleep_seconds = float(config.get("sleep_seconds_between_requests", 2))

    total_imported = 0
    queries: Iterable[Dict[str, Any]] = config.get("queries", [])
    for query in queries:
        query_name = query.get("name", f"{query.get('cityCode')}-{query.get('areaCode')}")
        logger.info("Start query: %s", query_name)
        try:
            query_page = client.open_query_page(query["cityCode"])
            captcha_path = captcha_dir / f"captcha_{query_name}_{int(time.time())}.png"
            client.download_captcha(query_page.captcha_key, captcha_path)
            print("\n請開啟 CAPTCHA 圖檔並輸入驗證碼：")
            print(captcha_path.resolve())
            captcha_input = input("CAPTCHA: ").strip()
            if not captcha_input:
                raise RuntimeError("CAPTCHA is empty")

            page = 1
            token = None
            while True:
                started_at = utc_now()
                job_key = make_job_key(query, page)
                logger.info("Start job=%s", job_key)
                try:
                    response = client.inquiry_date(
                        query=query,
                        csrf=query_page.csrf,
                        captcha_key=query_page.captcha_key,
                        captcha_input=captcha_input,
                        page=page,
                        rows=50,
                        token=token,
                    )
                    raw_path = save_raw(raw_dir, query, page, response)
                    records = parse_records(response, query, raw_path)
                    csv_path = save_csv(csv_dir, query, page, records)
                    imported = upsert_records(conn, records)
                    total_imported += imported
                    finished_at = utc_now()

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

                    token = response.get("token") or token
                    total_pages = int(response.get("total") or 1)
                    if page >= total_pages:
                        break
                    page += 1
                    time.sleep(sleep_seconds)
                except Exception as exc:
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
            logger.exception("Query failed before paging: %s", query_name)
        finally:
            time.sleep(sleep_seconds)

    logger.info("Crawler finished. imported_rows=%s db=%s", total_imported, db_path)
    conn.close()
    return total_imported


def run_scheduler(config_path: Path) -> None:
    config = load_conditions(config_path)
    daily_at = config.get("schedule", {}).get("daily_at", "02:00")
    print(f"Scheduler started. Daily run time: {daily_at}. Press Ctrl+C to stop.")
    last_run_date = None
    while True:
        now = datetime.now()
        current_hm = now.strftime("%H:%M")
        if current_hm == daily_at and last_run_date != now.date():
            run_once(load_conditions(config_path), config_path)
            last_run_date = now.date()
        time.sleep(30)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RIS 3053 doorplate crawler")
    parser.add_argument("--conditions", default="conditions.json", help="Path to conditions JSON")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--schedule", action="store_true", help="Run built-in daily scheduler")
    return parser.parse_args()


def main() -> int:
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
    raise SystemExit(main())
