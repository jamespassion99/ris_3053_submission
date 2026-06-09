"""Notification helper for writing abnormal events to 試題3.

通知設計採 JSONL 檔案：
- 試題1/試題2 寫入 ../試題3/notifications/notifications.jsonl。
- 試題3 log collector 讀取此檔案並在平台顯示。
- 若環境變數 NOTIFY_WEBHOOK_URL 有設定，也會嘗試 POST 到 webhook。
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def utc_now() -> str:
    """回傳 UTC ISO 時間字串。"""
    return datetime.now(timezone.utc).isoformat()


def default_notification_path(base_dir: Path) -> Path:
    """回傳預設通知 JSONL 路徑。

    base_dir 是試題1或試題2資料夾，因此 ../試題3/notifications/notifications.jsonl
    會指向同一個繳交專案內的試題3通知檔。
    """
    return (base_dir.parent / "試題3" / "notifications" / "notifications.jsonl").resolve()


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    """將 payload 追加到指定 JSONL 檔案。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def notify_event(
    notification_path: Path,
    service: str,
    severity: str,
    event_type: str,
    message: str,
    details: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """寫入一筆異常通知，必要時同步送 webhook。

    回傳 payload 方便呼叫端測試或延伸；即使 webhook 失敗也不會中斷主流程。
    """
    payload: Dict[str, Any] = {
        "created_at": utc_now(),
        "service": service,
        "severity": severity,
        "event_type": event_type,
        "message": message,
        "details": details or {},
    }
    notification_path.parent.mkdir(parents=True, exist_ok=True)
    with notification_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    _send_webhook_if_configured(payload)
    return payload


def _send_webhook_if_configured(payload: Dict[str, Any]) -> None:
    """若有設定 NOTIFY_WEBHOOK_URL，就把通知 payload POST 出去。"""
    webhook_url = os.environ.get("NOTIFY_WEBHOOK_URL", "").strip()
    if not webhook_url:
        return
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
    except Exception:
        # 通知不能影響爬蟲/API 主流程，因此 webhook 失敗只忽略。
        return
