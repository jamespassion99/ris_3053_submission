"""試題3：Log 收集器與異常通知平台。

這個服務使用 Python 標準庫建立簡易 HTTP 平台，可即時檢視：
- 試題1 爬蟲 info/error/job log。
- 試題2 API 查詢紀錄。
- 試題1/試題2 產生的異常通知紀錄。

執行：
  python main.py

開啟：
  http://127.0.0.1:9000
"""

from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import parse_qs, urlparse


LOG_SOURCES = {
    "crawler_info": "crawler_info_log",
    "crawler_error": "crawler_error_log",
    "crawler_job": "crawler_job_log",
    "api_query": "api_query_log",
    "notifications": "notifications_log",
}


def utc_now() -> str:
    """回傳 UTC ISO 時間，供平台 summary 顯示更新時間。"""
    return datetime.now(timezone.utc).isoformat()


def load_config(config_path: Path) -> Dict[str, Any]:
    """讀取試題3 config.json。"""
    with config_path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def resolve_path(config: Dict[str, Any], config_path: Path, key: str) -> Path:
    """將 config 中的相對路徑轉成絕對路徑。

    相對路徑以 config.json 所在資料夾為基準，因此專案整包搬移後仍可運作。
    """
    path = Path(config[key])
    if not path.is_absolute():
        path = (config_path.parent / path).resolve()
    return path


def tail_lines(path: Path, limit: int) -> List[str]:
    """讀取檔案最後 limit 行；檔案不存在時回空陣列。

    這裡採簡單 read_text 實作，足以應付考題與小型 log；正式大量 log 可改用 seek
    從檔尾讀取以降低記憶體使用。
    """
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-limit:]


def parse_jsonl_lines(lines: List[str]) -> List[Dict[str, Any]]:
    """嘗試把 JSONL 每一行轉成 dict；不能解析的行保留 raw 文字。"""
    parsed: List[Dict[str, Any]] = []
    for line in lines:
        try:
            value = json.loads(line)
            parsed.append(value if isinstance(value, dict) else {"raw": value})
        except json.JSONDecodeError:
            parsed.append({"raw": line})
    return parsed


def build_log_payload(config: Dict[str, Any], config_path: Path, source: str, limit: int) -> Dict[str, Any]:
    """依 source 讀取指定 log，回傳 API JSON payload。"""
    if source not in LOG_SOURCES:
        raise ValueError(f"unknown log source: {source}")
    path = resolve_path(config, config_path, LOG_SOURCES[source])
    lines = tail_lines(path, limit)
    return {
        "source": source,
        "path": str(path),
        "exists": path.exists(),
        "limit": limit,
        "line_count": len(lines),
        "lines": lines,
        "items": parse_jsonl_lines(lines) if source in {"crawler_job", "api_query", "notifications"} else [],
    }


def build_summary(config: Dict[str, Any], config_path: Path, limit: int) -> Dict[str, Any]:
    """彙整平台首頁需要的狀態摘要。"""
    logs = {source: build_log_payload(config, config_path, source, limit) for source in LOG_SOURCES}
    notification_items = logs["notifications"]["items"]
    error_notifications = [item for item in notification_items if item.get("severity") in {"error", "critical"}]
    return {
        "ok": True,
        "updated_at": utc_now(),
        "sources": {
            source: {
                "path": payload["path"],
                "exists": payload["exists"],
                "line_count": payload["line_count"],
            }
            for source, payload in logs.items()
        },
        "recent_notifications": notification_items[-10:],
        "error_notification_count_in_tail": len(error_notifications),
    }


def render_dashboard(config: Dict[str, Any], config_path: Path) -> str:
    """產生簡易 HTML dashboard，讓使用者不用前端框架即可檢視 log。"""
    limit = int(config.get("default_tail_lines", 100))
    summary = build_summary(config, config_path, limit)
    sections = []
    for source in LOG_SOURCES:
        payload = build_log_payload(config, config_path, source, min(limit, 50))
        escaped_lines = "\n".join(html.escape(line) for line in payload["lines"][-50:])
        sections.append(
            f"""
            <section class="card">
              <h2>{html.escape(source)}</h2>
              <p><strong>路徑：</strong>{html.escape(payload['path'])}</p>
              <p><strong>存在：</strong>{payload['exists']}，<strong>顯示行數：</strong>{payload['line_count']}</p>
              <p><a href="/api/logs?source={source}&limit={limit}">JSON API</a></p>
              <pre>{escaped_lines}</pre>
            </section>
            """
        )

    notification_rows = "".join(
        f"<li><strong>{html.escape(str(item.get('severity', '')))}</strong> "
        f"{html.escape(str(item.get('service', '')))} - {html.escape(str(item.get('message', '')))}</li>"
        for item in summary["recent_notifications"]
    ) or "<li>目前沒有通知</li>"

    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="10">
  <title>試題3 Log 收集器與異常通知平台</title>
  <style>
    body {{ font-family: Arial, 'Microsoft JhengHei', sans-serif; margin: 24px; background: #f6f8fa; color: #24292f; }}
    h1 {{ margin-bottom: 4px; }}
    .hint {{ color: #57606a; }}
    .card {{ background: white; border: 1px solid #d0d7de; border-radius: 8px; padding: 16px; margin: 16px 0; }}
    pre {{ background: #0d1117; color: #c9d1d9; padding: 12px; overflow: auto; max-height: 260px; border-radius: 6px; }}
    code {{ background: #eaeef2; padding: 2px 4px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>試題3 Log 收集器與異常通知平台</h1>
  <p class="hint">頁面每 10 秒自動刷新。更新時間：{html.escape(summary['updated_at'])}</p>
  <section class="card">
    <h2>最近異常通知</h2>
    <p>最近 tail 內 error/critical 通知數：{summary['error_notification_count_in_tail']}</p>
    <ul>{notification_rows}</ul>
  </section>
  {''.join(sections)}
</body>
</html>"""


class LogCollectorHandler(BaseHTTPRequestHandler):
    """試題3 HTTP handler，提供 HTML dashboard 與 JSON API。"""

    config: Dict[str, Any]
    config_path: Path

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler required name
        """路由 GET 請求：/ 顯示 dashboard，/api/* 回傳 JSON。"""
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        query = {key: values[-1] if values else "" for key, values in parse_qs(parsed.query).items()}

        try:
            if path == "/":
                self._send_html(HTTPStatus.OK, render_dashboard(self.config, self.config_path))
                return

            if path == "/api/summary":
                limit = self._read_int(query, "limit", int(self.config.get("default_tail_lines", 100)), 1, 1000)
                self._send_json(HTTPStatus.OK, build_summary(self.config, self.config_path, limit))
                return

            if path == "/api/logs":
                source = query.get("source", "notifications")
                limit = self._read_int(query, "limit", int(self.config.get("default_tail_lines", 100)), 1, 1000)
                self._send_json(HTTPStatus.OK, build_log_payload(self.config, self.config_path, source, limit))
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "endpoint_not_found"})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "bad_request", "message": str(exc)})
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal_error", "message": str(exc)})

    def log_message(self, format: str, *args: Any) -> None:
        """輸出 access log 到 console。"""
        print("%s - - [%s] %s" % (self.client_address[0], self.log_date_time_string(), format % args))

    def _send_json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        """回傳 JSON response。"""
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, status: HTTPStatus, html_text: str) -> None:
        """回傳 HTML dashboard。"""
        body = html_text.encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @staticmethod
    def _read_int(query: Dict[str, str], name: str, default: int, min_value: int, max_value: int) -> int:
        """讀取整數 query 參數並檢查範圍。"""
        raw_value = query.get(name, "")
        if raw_value == "":
            return default
        value = int(raw_value)
        if value < min_value or value > max_value:
            raise ValueError(f"{name} must be between {min_value} and {max_value}")
        return value


def create_handler(config: Dict[str, Any], config_path: Path) -> type[LogCollectorHandler]:
    """建立已注入 config 的 LogCollectorHandler class。"""
    class ConfiguredLogCollectorHandler(LogCollectorHandler):
        """實際交給 ThreadingHTTPServer 使用的 handler。"""

    ConfiguredLogCollectorHandler.config = config
    ConfiguredLogCollectorHandler.config_path = config_path
    return ConfiguredLogCollectorHandler


def parse_args() -> argparse.Namespace:
    """解析命令列參數。"""
    parser = argparse.ArgumentParser(description="RIS 3053 log collector and notification dashboard")
    parser.add_argument("--config", default="config.json", help="Path to config JSON")
    parser.add_argument("--host", help="Override host from config")
    parser.add_argument("--port", type=int, help="Override port from config")
    return parser.parse_args()


def main() -> int:
    """主程式：讀取 config 後啟動 Log collector HTTP server。"""
    args = parse_args()
    config_path = Path(args.config).resolve()
    config = load_config(config_path)
    host = args.host or config.get("host", "127.0.0.1")
    port = args.port or int(config.get("port", 9000))

    handler_class = create_handler(config, config_path)
    server = ThreadingHTTPServer((host, port), handler_class)
    print(f"RIS log collector running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping log collector...")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
