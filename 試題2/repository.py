"""SQLite data access layer for RIS API service."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple


class DatabaseNotReadyError(RuntimeError):
    """Raised when the crawler database has not been created yet."""


class RisRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path

    def health(self) -> Dict[str, Any]:
        exists = self.database_path.exists()
        if not exists:
            return {
                "ok": False,
                "database_exists": False,
                "database_path": str(self.database_path),
                "record_count": 0,
                "job_count": 0,
            }

        with self._connect() as conn:
            return {
                "ok": True,
                "database_exists": True,
                "database_path": str(self.database_path),
                "record_count": self._count_table(conn, "doorplate_record"),
                "job_count": self._count_table(conn, "crawl_job"),
            }

    def list_records(self, filters: Dict[str, str], limit: int, offset: int) -> Dict[str, Any]:
        where_sql, params = self._build_record_where(filters)
        sql = f"""
            SELECT
                id,
                city_code,
                area_code,
                address_text,
                register_date,
                register_kind_code,
                register_kind_name,
                raw_file_path,
                first_seen_at,
                last_seen_at
            FROM doorplate_record
            {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """
        count_sql = f"SELECT COUNT(*) AS total FROM doorplate_record {where_sql}"

        with self._connect() as conn:
            total = conn.execute(count_sql, params).fetchone()["total"]
            rows = conn.execute(sql, params + [limit, offset]).fetchall()
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": [dict(row) for row in rows],
            }

    def get_record(self, record_id: int) -> Dict[str, Any] | None:
        sql = """
            SELECT
                id,
                city_code,
                area_code,
                address_text,
                register_date,
                register_kind_code,
                register_kind_name,
                source_hash,
                raw_file_path,
                first_seen_at,
                last_seen_at
            FROM doorplate_record
            WHERE id = ?
        """
        with self._connect() as conn:
            row = conn.execute(sql, [record_id]).fetchone()
            return dict(row) if row else None

    def list_jobs(self, status: str, limit: int, offset: int) -> Dict[str, Any]:
        params: List[Any] = []
        where_sql = ""
        if status:
            where_sql = "WHERE status = ?"
            params.append(status)

        sql = f"""
            SELECT
                id,
                job_key,
                query_name,
                city_code,
                area_code,
                register_kind,
                s_date,
                e_date,
                page,
                status,
                raw_file_path,
                row_count,
                error_message,
                started_at,
                finished_at,
                created_at
            FROM crawl_job
            {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """
        count_sql = f"SELECT COUNT(*) AS total FROM crawl_job {where_sql}"

        with self._connect() as conn:
            total = conn.execute(count_sql, params).fetchone()["total"]
            rows = conn.execute(sql, params + [limit, offset]).fetchall()
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": [dict(row) for row in rows],
            }

    def _connect(self) -> sqlite3.Connection:
        if not self.database_path.exists():
            raise DatabaseNotReadyError(
                f"Database not found: {self.database_path}. Run the crawler first."
            )
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _count_table(conn: sqlite3.Connection, table_name: str) -> int:
        try:
            return int(conn.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()["total"])
        except sqlite3.Error:
            return 0

    @staticmethod
    def _build_record_where(filters: Dict[str, str]) -> Tuple[str, List[Any]]:
        clauses: List[str] = []
        params: List[Any] = []

        exact_fields = {
            "cityCode": "city_code",
            "areaCode": "area_code",
            "registerKind": "register_kind_code",
        }
        for query_name, column_name in exact_fields.items():
            value = filters.get(query_name, "").strip()
            if value:
                clauses.append(f"{column_name} = ?")
                params.append(value)

        date_from = filters.get("dateFrom", "").strip()
        if date_from:
            clauses.append("register_date >= ?")
            params.append(date_from)

        date_to = filters.get("dateTo", "").strip()
        if date_to:
            clauses.append("register_date <= ?")
            params.append(date_to)

        keyword = filters.get("q", "").strip()
        if keyword:
            clauses.append("address_text LIKE ?")
            params.append(f"%{keyword}%")

        if not clauses:
            return "", params
        return "WHERE " + " AND ".join(clauses), params
