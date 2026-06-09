"""SQLite data access layer for RIS API service."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple


class DatabaseNotReadyError(RuntimeError):
    """當爬蟲資料庫尚未建立或找不到時丟出的自訂例外。"""


class RisRepository:
    """集中管理 API 對 SQLite 的所有讀取操作。

    Handler 只負責 HTTP，真正的 SQL 都放在 repository，讓路由與資料存取分層清楚。
    """

    def __init__(self, database_path: Path) -> None:
        """保存 SQLite 路徑；實際連線在每次查詢時才建立。"""
        self.database_path = database_path

    def health(self) -> Dict[str, Any]:
        """回傳 API 健康狀態與資料庫基本統計。

        /health 會使用這個方法確認 DB 是否存在，以及 doorplate_record/crawl_job 筆數。
        """
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
        """依查詢參數取得門牌資料列表，並回傳 total/limit/offset/items。"""
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
            # total 使用同一組 WHERE 條件，讓前端知道符合條件總共有幾筆。
            total = conn.execute(count_sql, params).fetchone()["total"]
            rows = conn.execute(sql, params + [limit, offset]).fetchall()
            return {
                "total": total,
                "limit": limit,
                "offset": offset,
                "items": [dict(row) for row in rows],
            }

    def get_record(self, record_id: int) -> Dict[str, Any] | None:
        """依 id 查詢單筆門牌資料；查無資料時回傳 None。"""
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
            # 使用參數化查詢，避免將使用者輸入直接串進 SQL。
            row = conn.execute(sql, [record_id]).fetchone()
            return dict(row) if row else None

    def list_jobs(self, status: str, limit: int, offset: int) -> Dict[str, Any]:
        """查詢爬蟲 job 紀錄，可用 status 過濾 success/failed。"""
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
        """建立 SQLite 連線並設定 row_factory。

        row_factory 設為 sqlite3.Row 後，查詢結果可以用欄位名稱取值，轉 dict 也方便。
        """
        if not self.database_path.exists():
            raise DatabaseNotReadyError(
                f"Database not found: {self.database_path}. Run the crawler first."
            )
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _count_table(conn: sqlite3.Connection, table_name: str) -> int:
        """安全統計資料表筆數；若資料表不存在則回傳 0。"""
        try:
            return int(conn.execute(f"SELECT COUNT(*) AS total FROM {table_name}").fetchone()["total"])
        except sqlite3.Error:
            # DB 檔存在但 schema 尚未建立或損壞時，/health 仍能回應。
            return 0

    @staticmethod
    def _build_record_where(filters: Dict[str, str]) -> Tuple[str, List[Any]]:
        """根據 /records query string 組出 WHERE 子句與 SQL 參數。

        欄位名稱由程式白名單控制，值一律用 ? 參數帶入，避免 SQL injection。
        """
        clauses: List[str] = []
        params: List[Any] = []

        # API 參數名稱與 DB 欄位名稱不同，集中在這裡對應。
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
