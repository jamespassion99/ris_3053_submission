"""RIS 3053 API service.

A small dependency-free HTTP API for querying data collected by the crawler in
../ris_crawler_3053/data/ris_doorplate.sqlite3.
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

from repository import DatabaseNotReadyError, RisRepository


class JsonApiHandler(BaseHTTPRequestHandler):
    repository: RisRepository
    default_limit: int
    max_limit: int

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = self._flatten_query(parse_qs(parsed.query))

        try:
            if path == "/" or path == "/health":
                self._send_json(HTTPStatus.OK, self.repository.health())
                return

            if path == "/records":
                limit = self._read_int(query, "limit", self.default_limit, 1, self.max_limit)
                offset = self._read_int(query, "offset", 0, 0, 10_000_000)
                data = self.repository.list_records(query, limit=limit, offset=offset)
                self._send_json(HTTPStatus.OK, data)
                return

            record_match = re.fullmatch(r"/records/(\d+)", path)
            if record_match:
                record_id = int(record_match.group(1))
                record = self.repository.get_record(record_id)
                if record is None:
                    self._send_json(HTTPStatus.NOT_FOUND, {"error": "record_not_found"})
                    return
                self._send_json(HTTPStatus.OK, record)
                return

            if path == "/jobs":
                limit = self._read_int(query, "limit", self.default_limit, 1, self.max_limit)
                offset = self._read_int(query, "offset", 0, 0, 10_000_000)
                status = query.get("status", "")
                data = self.repository.list_jobs(status=status, limit=limit, offset=offset)
                self._send_json(HTTPStatus.OK, data)
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "endpoint_not_found"})
        except DatabaseNotReadyError as exc:
            self._send_json(HTTPStatus.SERVICE_UNAVAILABLE, {"error": "database_not_ready", "message": str(exc)})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad_request", "message": str(exc)})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal_error", "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        print("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _flatten_query(raw_query: Dict[str, list[str]]) -> Dict[str, str]:
        return {key: values[-1] if values else "" for key, values in raw_query.items()}

    @staticmethod
    def _read_int(query: Dict[str, str], name: str, default: int, min_value: int, max_value: int) -> int:
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
    with config_path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def create_handler(config: Dict[str, Any], config_path: Path) -> type[JsonApiHandler]:
    database_path = Path(config["database_path"])
    if not database_path.is_absolute():
        database_path = (config_path.parent / database_path).resolve()

    class ConfiguredHandler(JsonApiHandler):
        repository = RisRepository(database_path)
        default_limit = int(config.get("default_limit", 50))
        max_limit = int(config.get("max_limit", 500))

    return ConfiguredHandler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RIS 3053 API service")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    parser.add_argument("--host", help="Override host from config")
    parser.add_argument("--port", type=int, help="Override port from config")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
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
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
