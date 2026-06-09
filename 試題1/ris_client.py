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
    """保存進入查詢頁後取得的必要欄位。

    csrf：網站表單防偽 token。
    captcha_key：下載與提交驗證碼時使用的 key。
    html：查詢頁 HTML，保留給除錯或未來解析欄位使用。
    """

    csrf: str
    captcha_key: str
    html: str


class RisClient:
    """封裝 RIS 網站 HTTP 流程，讓主程式不用處理細節。

    這個類別負責：
    - 維持 CookieJar session。
    - 取得 CSRF token。
    - 下載 CAPTCHA 圖片。
    - 送出「以編釘日期、編釘類別查詢」POST。
    """

    # 這些路徑是從網站操作流程分析出來的 endpoint。
    MAIN_PATH = "/info-doorplate/app/doorplate/main"
    MAP_PATH = "/info-doorplate/app/doorplate/map"
    QUERY_PATH = "/info-doorplate/app/doorplate/query"
    INQUIRY_DATE_PATH = "/info-doorplate/app/doorplate/inquiry/date"
    CAPTCHA_IMAGE_PATH = "/info-doorplate/captcha/image"

    def __init__(self, base_url: str, timeout: int = 30) -> None:
        """建立 RIS HTTP client。

        base_url 通常是 https://www.ris.gov.tw；timeout 用來避免網站無回應時
        程式永久卡住。CookieJar 讓 main/map/query/inquiry 共用同一個 session。
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.cookie_jar = CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )
        # 使用接近瀏覽器的 header，降低被網站視為非正常請求的機率。
        self.default_headers = {
            "User-Agent": "Mozilla/5.0 RIS-doorplate-crawler/1.0 (+operator-assisted)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.6",
        }

    def open_query_page(self, city_code: str) -> QueryPage:
        """依序進入 main -> map -> query 頁，取得 CSRF 與 captchaKey。

        RIS 網站的查詢 API 不是直接打 inquiry endpoint 就能使用，需要先走頁面
        流程讓 server 建立 session 狀態並產生隱藏欄位。
        """
        # 第一步：GET main 頁，從 HTML 取得第一個 CSRF token。
        main_html = self._request("GET", self.MAIN_PATH).decode("utf-8", errors="replace")
        csrf = self._parse_csrf(main_html)

        # 第二步：POST 到 map，指定 searchType=date，表示使用日期/類別查詢。
        map_html = self._request(
            "POST",
            self.MAP_PATH,
            form={"searchType": "date", "_csrf": csrf},
            referer=self.MAIN_PATH,
        ).decode("utf-8", errors="replace")
        csrf = self._parse_csrf(map_html) or csrf

        # 第三步：POST 到 query，帶入 cityCode，取得真正的查詢頁與 CAPTCHA key。
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
        """下載 CAPTCHA 圖片到本機，回傳圖片路徑。

        加上 time query 參數是為了模擬瀏覽器避免圖片快取，確保每次看到最新圖。
        """
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
        """送出一頁「以編釘日期、編釘類別查詢」，回傳網站 JSON。

        query 來自 conditions.json；csrf/captcha_key 來自 open_query_page；
        captcha_input 是人工輸入。page/rows 對應網站 jqGrid 分頁參數。
        """
        # 表單欄位名稱必須對應網站實際 endpoint，否則 server 不會回正確資料。
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
            # 部分分頁流程會回傳 token；帶回去可延續 server 查詢狀態。
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
            # 網站變更、CAPTCHA 過期或錯誤頁都可能造成非 JSON 回應。
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
        """共用 HTTP request helper，統一處理 URL、headers、form 與錯誤訊息。"""
        url = path if path.startswith("http") else self.base_url + path
        data = None
        headers = dict(self.default_headers)
        if accept:
            headers["Accept"] = accept
        if referer:
            headers["Referer"] = referer if referer.startswith("http") else self.base_url + referer
        if form is not None:
            # RIS 使用 x-www-form-urlencoded 表單，不是 JSON body。
            data = urllib.parse.urlencode(form).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        if extra_headers:
            headers.update(extra_headers)

        request = urllib.request.Request(url=url, data=data, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            # 保留部分 body，方便看出是 403、驗證錯誤或網站錯誤頁。
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Network error for {url}: {exc}") from exc

    @staticmethod
    def _parse_csrf(html: str) -> str:
        """從 HTML 隱藏欄位解析 _csrf token。"""
        return RisClient._parse_input_value(html, "_csrf")

    @staticmethod
    def _parse_input_value(html: str, name: str) -> str:
        """從 input tag 解析指定 name 的 value。

        網站 HTML 屬性順序不一定固定，所以同時支援 name 在 value 前面與後面。
        """
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
