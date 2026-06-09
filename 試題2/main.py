"""RIS 3053 API service.

A small dependency-free HTTP API for querying data collected by the crawler in
../試題1/data/ris_doorplate.sqlite3.
"""

from __future__ import annotations

import argparse
import json
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from notification import append_jsonl, default_notification_path, notify_event, utc_now
from repository import DatabaseNotReadyError, RisRepository


class JsonApiHandler(BaseHTTPRequestHandler):
    """HTTP request handler，負責將 URL 路由到對應 repository 查詢。

    repository/default_limit/max_limit 由 create_handler 動態注入，讓 handler 可以
    依不同 config 啟動，不必把設定寫死在 class 裡。
    """

    repository: RisRepository
    default_limit: int
    max_limit: int
    query_log_path: Path
    notification_path: Path

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        """處理所有 GET API 請求。

        支援：
        - /health：健康檢查。
        - /records：查多筆門牌資料。
        - /records/{id}：查單筆門牌資料。
        - /jobs：查爬蟲任務紀錄。
        """
        # 先拆 URL，將 path 與 query string 分開處理。
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = self._flatten_query(parse_qs(parsed.query))

        try:
            # 根路徑也視為 health，方便瀏覽器直接打開確認服務狀態。
            if path == "/" or path == "/health":
                self._send_json(HTTPStatus.OK, self.repository.health())
                return

            if path == "/records":
                # limit/offset 都經過範圍檢查，避免一次回傳太多資料。
                limit = self._read_int(query, "limit", self.default_limit, 1, self.max_limit)
                offset = self._read_int(query, "offset", 0, 0, 10_000_000)
                data = self.repository.list_records(query, limit=limit, offset=offset)
                self._record_api_query(path, query, HTTPStatus.OK, data.get("total", 0))
                if data.get("total", 0) == 0:
                    notify_event(
                        self.notification_path,
                        service="試題2 API",
                        severity="warning",
                        event_type="api_empty_result",
                        message="/records 查詢結果為空",
                        details={"path": path, "query": query, "limit": limit, "offset": offset},
                    )
                self._send_json(HTTPStatus.OK, data)
                return

            # /records/123 這類路徑用正規表示式取出 id。
            record_match = re.fullmatch(r"/records/(\d+)", path)
            if record_match:
                record_id = int(record_match.group(1))
                record = self.repository.get_record(record_id)
                if record is None:
                    self._record_api_query(path, query, HTTPStatus.NOT_FOUND, 0)
                    notify_event(
                        self.notification_path,
                        service="試題2 API",
                        severity="warning",
                        event_type="api_empty_result",
                        message=f"/records/{record_id} 查無資料",
                        details={"path": path, "record_id": record_id},
                    )
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "record_not_found"})
                    return
                self._record_api_query(path, query, HTTPStatus.OK, 1)
                self._send_json(HTTPStatus.OK, record)
                return

            if path == "/jobs":
                limit = self._read_int(query, "limit", self.default_limit, 1, self.max_limit)
                offset = self._read_int(query, "offset", 0, 0, 10_000_000)
                status = query.get("status", "")
                data = self.repository.list_jobs(status=status, limit=limit, offset=offset)
                self._record_api_query(path, query, HTTPStatus.OK, data.get("total", 0))
                self._send_json(HTTPStatus.OK, data)
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "endpoint_not_found"})
        except DatabaseNotReadyError as exc:
            # 試題1尚未執行或 DB path 設定錯誤時，回 503 表示服務暫不可用。
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "database_not_ready", "message": str(exc)})
        except ValueError as exc:
            # 參數格式錯誤，例如 limit=abc，回 400 給使用者修正。
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad_request", "message": str(exc)})
        except Exception as exc:
            # 防止未知錯誤讓 server crash；實務上可在此加檔案 log。
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal_error", "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        """覆寫預設 access log 格式，讓 console 顯示每次 request。"""
        print("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        """統一輸出 JSON response，並設定 Content-Type、Content-Length 與 CORS。"""
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        # 允許瀏覽器前端直接呼叫；若正式上線可改成指定網域。
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


    def _record_api_query(self, path: str, query: Dict[str, str], status: HTTPStatus, result_count: int) -> None:
        """將 API 查詢紀錄寫入 JSONL，供試題3平台檢視。"""
        append_jsonl(
            self.query_log_path,
            {
                "created_at": utc_now(),
                "client_ip": self.client_address[0],
                "path": path,
                "query": query,
                "status": status.value,
                "result_count": result_count,
            },
        )

    @staticmethod
    def _flatten_query(raw_query: Dict[str, list[str]]) -> Dict[str, str]:
        """將 parse_qs 產生的 list value 攤平成單一字串 value。"""
        return {key: values[-1] if values else "" for key, values in raw_query.items()}

    @staticmethod
    def _read_int(query: Dict[str, str], name: str, default: int, min_value: int, max_value: int) -> int:
        """讀取並驗證整數 query 參數。

        沒提供參數時回傳 default；有提供但不是整數或超出範圍時丟 ValueError，
        由 do_GET 統一轉成 HTTP 400。
        """
        raw_value = query.get(name, "")
        if raw_value == "":
            return default
        try:
            value = int(raw_value)
        except ValueError as exc:
            raise ValueError(f"{name} must be an integer") from exc
        if value < min_value or value > max_value:
            raise ValueError(f"{name} must be between {min_value} and {max_value}")
        return value


def load_config(config_path: Path) -> Dict[str, Any]:
    """讀取 API config.json，回傳 dict。"""
    with config_path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def create_handler(config: Dict[str, Any], config_path: Path) -> type[JsonApiHandler]:
    """依 config 建立已綁定 repository 與分頁設定的 Handler class。

    BaseHTTPRequestHandler 是由 HTTP server 自行實例化，因此較簡單的做法是用
    class attribute 注入共用設定。
    """
    database_path = Path(config["database_path"])
    if not database_path.is_absolute():
        # 相對路徑以 config.json 所在資料夾為基準，避免從不同 cwd 啟動時找不到 DB。
        database_path = (config_path.parent / database_path).resolve()

    log_dir = Path(config.get("log_dir", "logs"))
    if not log_dir.is_absolute():
        log_dir = (config_path.parent / log_dir).resolve()
    query_log_path = log_dir / "api-query.jsonl"
    notification_path = default_notification_path(config_path.parent)

    class ConfiguredHandler(JsonApiHandler):
        """帶入 config 後的實際 handler class。"""

    ConfiguredHandler.repository = RisRepository(database_path)
    ConfiguredHandler.default_limit = int(config.get("default_limit", 50))
    ConfiguredHandler.max_limit = int(config.get("max_limit", 500))
    ConfiguredHandler.query_log_path = query_log_path
    ConfiguredHandler.notification_path = notification_path
    return ConfiguredHandler


def parse_args() -> argparse.Namespace:
    """解析 API server 命令列參數，允許覆蓋 config 的 host/port。"""
    parser = argparse.ArgumentParser(description="RIS 3053 API service")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    parser.add_argument("--host", help="Override host from config")
    parser.add_argument("--port", type=int, help="Override port from config")
    return parser.parse_args()


def main() -> int:
    """API server 主入口：讀設定、建立 server、開始監聽。"""
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)

    # 命令列參數優先於 config，方便臨時改 port 測試。
    host = args.host or config.get("host", "127.0.0.1")
    port = args.port or int(config.get("port", 8000))

    handler_class = create_handler(config, config_path)
    server = ThreadingHTTPServer((host, port), handler_class)
    print(f"RIS API service running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping API service...")
    finally:
        # 釋放 socket，避免下次啟動時 port 還被佔用。
        server.server_close()
    return 0


if __name__ == "__main__":
    # 將 main 的回傳值轉成 process exit code。
    raise SystemExit(main())
