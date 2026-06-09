"""RIS doorplate crawler HTTP client.

This module intentionally does not bypass CAPTCHA.  It can download the
CAPTCHA image for a human/operator to read and then submits the value typed by
that operator.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass
class QueryPage:
    csrf: str
    captcha_key: str
    html: str


class RisClient:
    MAIN_PATH = "/info-doorplate/app/doorplate/main"
    MAP_PATH = "/info-doorplate/app/doorplate/map"
    QUERY_PATH = "/info-doorplate/app/doorplate/query"
    INQUIRY_DATE_PATH = "/info-doorplate/app/doorplate/inquiry/date"
    CAPTCHA_IMAGE_PATH = "/info-doorplate/captcha/image"

    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cookie_jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 RIS-doorplate-crawler/1.0 (+operator-assisted)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.6",
        }

    def open_query_page(self, city_code: str) -> QueryPage:
        """Navigate main -> map -> query page and return CSRF/CAPTCHA data."""
        main_html = self._request("GET", self.MAIN_PATH).decode("utf-8", errors="replace")
        csrf = self._parse_csrf(main_html)

        map_html = self._request(
            "POST",
            self.MAP_PATH,
            form={"searchType": "date", "_csrf": csrf},
            referer=self.MAIN_PATH,
        ).decode("utf-8", errors="replace")
        csrf = self._parse_csrf(map_html) or csrf

        query_html = self._request(
            "POST",
            self.QUERY_PATH,
            form={"searchType": "date", "cityCode": city_code, "_csrf": csrf},
            referer=self.MAP_PATH,
        ).decode("utf-8", errors="replace")

        query_csrf = self._parse_csrf(query_html)
        captcha_key = self._parse_input_value(query_html, "captchaKey")
        if not query_csrf:
            raise RuntimeError("Cannot find _csrf on query page")
        if not captcha_key:
            raise RuntimeError("Cannot find captchaKey on query page")
        return QueryPage(csrf=query_csrf, captcha_key=captcha_key, html=query_html)

    def download_captcha(self, captcha_key: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        query = urllib.parse.urlencode({"CAPTCHA_KEY": captcha_key, "time": int(time.time() * 1000)})
        body = self._request("GET", f"{self.CAPTCHA_IMAGE_PATH}?{query}", accept="image/*")
        output_path.write_bytes(body)
        return output_path

    def inquiry_date(
        self,
        query: Dict[str, Any],
        csrf: str,
        captcha_key: str,
        captcha_input: str,
        page: int = 1,
        rows: int = 50,
        token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Submit one jqGrid page for the date/register-kind search."""
        form = {
            "searchType": "date",
            "cityCode": query["cityCode"],
            "areaCode": query["areaCode"],
            "village": query.get("village", ""),
            "neighbor": query.get("neighbor", ""),
            "sDate": query["sDate"],
            "eDate": query["eDate"],
            "includeNoDate": "true" if query.get("includeNoDate") else "false",
            "registerKind": query.get("registerKind", "0"),
            "captchaInput": captcha_input,
            "captchaKey": captcha_key,
            "tkt": query.get("tkt", "-1"),
            "_csrf": csrf,
            "page": str(page),
            "rows": str(rows),
            "sidx": "",
            "sord": "asc",
            "_search": "false",
            "nd": str(int(time.time() * 1000)),
        }
        if token:
            form["token"] = token

        raw = self._request(
            "POST",
            self.INQUIRY_DATE_PATH,
            form=form,
            referer=self.QUERY_PATH,
            accept="application/json, text/javascript, */*; q=0.01",
            extra_headers={"X-Requested-With": "XMLHttpRequest"},
        )
        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Server did not return JSON: {text[:300]}") from exc
        return data

    def _request(
        self,
        method: str,
        path: str,
        form: Optional[Dict[str, Any]] = None,
        referer: Optional[str] = None,
        accept: Optional[str] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> bytes:
        url = path if path.startswith("http") else self.base_url + path
        data = None
        headers = dict(self.default_headers)
        if accept:
            headers["Accept"] = accept
        if referer:
            headers["Referer"] = referer if referer.startswith("http") else self.base_url + referer
        if form is not None:
            data = urllib.parse.urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        if extra_headers:
            headers.update(extra_headers)

        request = urllib.request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error for {url}: {exc}") from exc

    @staticmethod
    def _parse_csrf(html: str) -> str:
        return RisClient._parse_input_value(html, "_csrf")

    @staticmethod
    def _parse_input_value(html: str, name: str) -> str:
        # Handles both: name="x" value="y" and value="y" name="x".
        patterns = [
            rf'<input[^>]+name=["\']{re.escape(name)}["\'][^>]*value=["\']([^"\']*)["\']',
            rf'<input[^>]+value=["\']([^"\']*)["\'][^>]*name=["\']{re.escape(name)}["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return ""
