"""Storage, logging, and parsing helpers for RIS doorplate crawler."""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import sqlite3
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

# 網站 registerKind 以代碼回傳；這裡提供代碼與中文名稱對照，方便 CSV/API 閱讀。
REGISTER_KIND_NAMES = {
    "0": "資料維護",
    "1": "門牌初編",
    "2": "門牌改編",
    "3": "門牌增編",
    "4": "門牌合併",
    "5": "門牌廢止",
    "6": "行政區域調整",
    "7": "門牌整編",
}


def setup_logging(log_dir: Path) -> logging.Logger:
    """建立爬蟲 logger，同時輸出到 console、info log、error log。

    使用 RotatingFileHandler 避免長期排程執行時單一 log 檔無限長大。
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ris_crawler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    # 一般執行紀錄：開始、成功、匯入筆數、輸出檔案位置。
    info_handler = RotatingFileHandler(log_dir / "crawler-info.log", maxBytes=10_000_000, backupCount=10, encoding="utf-8")
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    # 錯誤紀錄：HTTP 失敗、解析失敗、DB 寫入失敗等。
    error_handler = RotatingFileHandler(log_dir / "crawler-error.log", maxBytes=10_000_000, backupCount=10, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # console_handler 讓人工執行時可以即時看到進度。
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    return logger


def utc_now() -> str:
    """回傳 ISO-8601 UTC 時間字串，用於資料庫與 JSONL log。"""
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: Path) -> sqlite3.Connection:
    """初始化 SQLite 資料庫與必要資料表，並回傳連線。

    crawl_job 用來記錄每一頁爬取成功/失敗；doorplate_record 用來存放整理後
    的門牌資料。CREATE TABLE IF NOT EXISTS 讓程式可重複執行。
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    # WAL 模式較適合「爬蟲寫入、API 讀取」並存的情境。
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS crawl_job (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_key TEXT NOT NULL UNIQUE,
            query_name TEXT,
            city_code TEXT,
            area_code TEXT,
            register_kind TEXT,
            s_date TEXT,
            e_date TEXT,
            page INTEGER,
            status TEXT NOT NULL,
            raw_file_path TEXT,
            row_count INTEGER DEFAULT 0,
            error_message TEXT,
            started_at TEXT,
            finished_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS doorplate_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_code TEXT NOT NULL,
            area_code TEXT NOT NULL,
            address_text TEXT NOT NULL,
            register_date TEXT,
            register_kind_code TEXT,
            register_kind_name TEXT,
            source_hash TEXT NOT NULL UNIQUE,
            raw_file_path TEXT,
            first_seen_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def make_job_key(query: Dict[str, Any], page: int) -> str:
    """組出每個 query + page 的唯一任務鍵，供 crawl_job 去重更新。"""
    parts = [
        query.get("name", "query"),
        query["cityCode"],
        query["areaCode"],
        query.get("registerKind", "0"),
        query["sDate"].replace("/", ""),
        query["eDate"].replace("/", ""),
        f"p{page}",
    ]
    return "-".join(parts)


def save_raw(raw_dir: Path, query: Dict[str, Any], page: int, response: Dict[str, Any]) -> Path:
    """將網站原始 JSON response 包成 envelope 後落檔。

    raw 檔保留 query、page、抓取時間與完整 response，若網站欄位變更，可以不用
    重爬網站，直接用 raw 檔重寫 parser。
    """
    date_dir = datetime.now().strftime("%Y-%m-%d")
    target_dir = (
        raw_dir
        / date_dir
        / f"city={query['cityCode']}"
        / f"area={query['areaCode']}"
        / f"kind={query.get('registerKind', '0')}"
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"sdate={query['sDate'].replace('/', '')}_edate={query['eDate'].replace('/', '')}_page={page}.json"
    path = target_dir / filename
    envelope = {
        "source": "ris.gov.tw/info-doorplate",
        "query": query,
        "page": page,
        "fetched_at": utc_now(),
        "response": response,
    }
    path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_csv(csv_dir: Path, query: Dict[str, Any], page: int, records: Iterable[Dict[str, str]]) -> Path:
    """將解析後資料輸出為 CSV，滿足題目「清理並結構化後存 CSV」要求。"""
    date_dir = datetime.now().strftime("%Y-%m-%d")
    target_dir = (
        csv_dir
        / date_dir
        / f"city={query['cityCode']}"
        / f"area={query['areaCode']}"
        / f"kind={query.get('registerKind', '0')}"
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"sdate={query['sDate'].replace('/', '')}_edate={query['eDate'].replace('/', '')}_page={page}.csv"
    path = target_dir / filename

    # Iterable 可能是 generator，先轉 list 可同時支援 writerows 與未來統計筆數。
    rows = list(records)
    fieldnames = [
        "city_code",
        "area_code",
        "address_text",
        "register_date",
        "register_kind_code",
        "register_kind_name",
        "source_hash",
        "raw_file_path",
    ]
    # utf-8-sig 讓 Excel 開啟中文 CSV 時比較不容易亂碼。
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def append_job_log(log_dir: Path, payload: Dict[str, Any]) -> None:
    """將單筆 job 事件追加到 JSONL log。

    JSONL 一行一筆，方便 grep，也方便後續送到 log monitoring 平台。
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / "crawler-job.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def record_job(
    conn: sqlite3.Connection,
    query: Dict[str, Any],
    page: int,
    status: str,
    raw_file_path: str = "",
    row_count: int = 0,
    error_message: str = "",
    started_at: str = "",
    finished_at: str = "",
) -> None:
    """將每頁爬蟲任務結果寫入 crawl_job。

    job_key 設為 UNIQUE，同一條件同一頁重跑時會更新狀態，而不是一直新增重複紀錄。
    """
    conn.execute(
        """
        INSERT INTO crawl_job (
            job_key, query_name, city_code, area_code, register_kind, s_date, e_date,
            page, status, raw_file_path, row_count, error_message, started_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_key) DO UPDATE SET
            status=excluded.status,
            raw_file_path=excluded.raw_file_path,
            row_count=excluded.row_count,
            error_message=excluded.error_message,
            started_at=excluded.started_at,
            finished_at=excluded.finished_at
        """,
        (
            make_job_key(query, page),
            query.get("name", ""),
            query.get("cityCode", ""),
            query.get("areaCode", ""),
            query.get("registerKind", ""),
            query.get("sDate", ""),
            query.get("eDate", ""),
            page,
            status,
            raw_file_path,
            row_count,
            # 避免過長錯誤訊息塞爆資料庫欄位或影響 API 回傳。
            error_message[:2000],
            started_at,
            finished_at,
        ),
    )
    conn.commit()


def parse_records(response: Dict[str, Any], query: Dict[str, Any], raw_file_path: Path) -> List[Dict[str, str]]:
    """把 RIS JSON response 的 rows 轉成固定欄位 record list。

    這裡是網站欄位格式與本地資料表格式的轉換層；若網站改欄位，主要調整這裡與
    _extract_row 即可。
    """
    rows = response.get("rows") or []
    parsed: List[Dict[str, str]] = []
    for row in rows:
        address, register_date, kind_code = _extract_row(row)
        if not address:
            # 沒地址代表這列不可用，避免寫入空資料。
            continue
        kind_code = str(kind_code or query.get("registerKind", ""))
        source_hash = _hash_record(query, address, register_date, kind_code)
        parsed.append(
            {
                "city_code": query["cityCode"],
                "area_code": query["areaCode"],
                "address_text": address,
                "register_date": register_date,
                "register_kind_code": kind_code,
                "register_kind_name": REGISTER_KIND_NAMES.get(kind_code, kind_code),
                "source_hash": source_hash,
                "raw_file_path": str(raw_file_path),
            }
        )
    return parsed


def upsert_records(conn: sqlite3.Connection, records: Iterable[Dict[str, str]]) -> int:
    """將解析後 records 寫入 doorplate_record，已存在則更新 raw 路徑與 last_seen_at。"""
    now = utc_now()
    count = 0
    for r in records:
        conn.execute(
            """
            INSERT INTO doorplate_record (
                city_code, area_code, address_text, register_date, register_kind_code,
                register_kind_name, source_hash, raw_file_path, first_seen_at, last_seen_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(source_hash) DO UPDATE SET
                raw_file_path=excluded.raw_file_path,
                last_seen_at=excluded.last_seen_at
            """,
            (
                r["city_code"],
                r["area_code"],
                r["address_text"],
                r["register_date"],
                r["register_kind_code"],
                r["register_kind_name"],
                r["source_hash"],
                r["raw_file_path"],
                now,
                now,
            ),
        )
        count += 1
    conn.commit()
    return count


def _extract_row(row: Any) -> Tuple[str, str, str]:
    """從網站 row 物件取出 address、register_date、kind_code。

    RIS/jqGrid 回傳可能是 dict + cell list、dict + v1/v2/v3，或直接 list。
    這個函式用多格式兼容方式提高抗網站微幅變更能力。
    """
    if isinstance(row, dict):
        if "cell" in row and isinstance(row["cell"], list):
            cell = row["cell"]
            return _clean(cell[0] if len(cell) > 0 else ""), _clean(cell[1] if len(cell) > 1 else ""), _clean(cell[2] if len(cell) > 2 else "")
        return _clean(row.get("v1", "")), _clean(row.get("v2", "")), _clean(row.get("v3", ""))
    if isinstance(row, list):
        return _clean(row[0] if len(row) > 0 else ""), _clean(row[1] if len(row) > 1 else ""), _clean(row[2] if len(row) > 2 else "")
    return "", "", ""


def _clean(value: Any) -> str:
    """將欄位值轉成字串並去除前後空白，確保輸出格式一致。"""
    return str(value or "").strip()


def _hash_record(query: Dict[str, Any], address: str, register_date: str, kind_code: str) -> str:
    """依行政區、地址、日期、編釘類別產生穩定 hash，用於去重 upsert。"""
    key = "|".join([query["cityCode"], query["areaCode"], address, register_date, kind_code])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
