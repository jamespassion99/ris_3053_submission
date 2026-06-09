"""Storage, logging, and parsing helpers for RIS doorplate crawler."""

from __future__ import annotations

import hashlib
import csv
import json
import logging
import sqlite3
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

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
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("ris_crawler")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    info_handler = RotatingFileHandler(log_dir / "crawler-info.log", maxBytes=10_000_000, backupCount=10, encoding="utf-8")
    info_handler.setLevel(logging.INFO)
    info_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(log_dir / "crawler-error.log", maxBytes=10_000_000, backupCount=10, encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(info_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)
    return logger


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
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
    """Save parsed records to CSV before the database upsert step."""
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
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return path


def append_job_log(log_dir: Path, payload: Dict[str, Any]) -> None:
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
            error_message[:2000],
            started_at,
            finished_at,
        ),
    )
    conn.commit()


def parse_records(response: Dict[str, Any], query: Dict[str, Any], raw_file_path: Path) -> List[Dict[str, str]]:
    rows = response.get("rows") or []
    parsed: List[Dict[str, str]] = []
    for row in rows:
        address, register_date, kind_code = _extract_row(row)
        if not address:
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
    if isinstance(row, dict):
        if "cell" in row and isinstance(row["cell"], list):
            cell = row["cell"]
            return _clean(cell[0] if len(cell) > 0 else ""), _clean(cell[1] if len(cell) > 1 else ""), _clean(cell[2] if len(cell) > 2 else "")
        return _clean(row.get("v1", "")), _clean(row.get("v2", "")), _clean(row.get("v3", ""))
    if isinstance(row, list):
        return _clean(row[0] if len(row) > 0 else ""), _clean(row[1] if len(row) > 1 else ""), _clean(row[2] if len(row) > 2 else "")
    return "", "", ""


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _hash_record(query: Dict[str, Any], address: str, register_date: str, kind_code: str) -> str:
    key = "|".join([query["cityCode"], query["areaCode"], address, register_date, kind_code])
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
