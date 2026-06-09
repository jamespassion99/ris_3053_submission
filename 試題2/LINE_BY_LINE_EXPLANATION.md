# RIS 3053 後端 API 逐行說明
本文件說明 `ris_api_service_3053` 後端 API 專案中主要程式檔的每一行用途。

## 專案用途
這個後端 API 使用 Python 標準庫 `http.server` 提供 HTTP API，並透過 `sqlite3` 讀取 `ris_crawler_3053` 爬蟲先前寫入的 SQLite 資料庫。

## 檔案角色
- `main.py`：HTTP API 入口，負責路由、參數解析、JSON 回應與啟動 server。
- `repository.py`：資料庫存取層，負責健康檢查、查門牌資料、查單筆資料、查爬蟲 job。
- `config.json`：API host、port、database path、分頁限制設定。

> 註：`README.md` 是使用說明文件，`__pycache__` 是 Python 自動產生的快取，不列入逐行程式說明。

## `main.py` 逐行說明
| 行號 | 原始碼 | 說明 |
| ---: | --- | --- |
| 1 | <code>&quot;&quot;&quot;RIS&nbsp;3053&nbsp;API&nbsp;service.</code> | 模組說明字串開頭，宣告這個檔案是 RIS 3053 API service。 |
| 2 | （空行） | 文件字串中的空白行，用來分隔標題與詳細說明。 |
| 3 | <code>A&nbsp;small&nbsp;dependency-free&nbsp;HTTP&nbsp;API&nbsp;for&nbsp;querying&nbsp;data&nbsp;collected&nbsp;by&nbsp;the&nbsp;crawler&nbsp;in</code> | 說明這是一個不依賴第三方套件的小型 HTTP API，用來查詢爬蟲蒐集到的資料。 |
| 4 | <code>../ris_crawler_3053/data/ris_doorplate.sqlite3.</code> | 標示資料來源 SQLite 檔案的相對路徑。 |
| 5 | <code>&quot;&quot;&quot;</code> | 模組說明字串結束。 |
| 6 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 7 | <code>from&nbsp;__future__&nbsp;import&nbsp;annotations</code> | 啟用延後解析型別註解，讓型別提示可以引用尚未完全載入的型別。 |
| 8 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 9 | <code>import&nbsp;argparse</code> | 匯入 argparse，用來解析命令列參數。 |
| 10 | <code>import&nbsp;json</code> | 匯入 json，用來把 Python dict 轉成 JSON 回應、也用來讀 config。 |
| 11 | <code>import&nbsp;re</code> | 匯入 re，用來用正規表示式比對 /records/{id} 路徑。 |
| 12 | <code>from&nbsp;http&nbsp;import&nbsp;HTTPStatus</code> | 匯入 HTTPStatus，讓 HTTP 狀態碼用語意化名稱表示，例如 OK、NOT_FOUND。 |
| 13 | <code>from&nbsp;http.server&nbsp;import&nbsp;BaseHTTPRequestHandler,&nbsp;ThreadingHTTPServer</code> | 匯入標準庫 HTTP handler 與多執行緒 HTTP server。 |
| 14 | <code>from&nbsp;pathlib&nbsp;import&nbsp;Path</code> | 匯入 Path，方便處理 config 與 database 路徑。 |
| 15 | <code>from&nbsp;typing&nbsp;import&nbsp;Any,&nbsp;Dict</code> | 匯入 Any、Dict 型別提示。 |
| 16 | <code>from&nbsp;urllib.parse&nbsp;import&nbsp;parse_qs,&nbsp;urlparse</code> | 匯入 URL 解析工具：parse_qs 解析 query string，urlparse 解析完整路徑。 |
| 17 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 18 | <code>from&nbsp;repository&nbsp;import&nbsp;DatabaseNotReadyError,&nbsp;RisRepository</code> | 從 repository.py 匯入資料庫尚未就緒的例外與資料存取類別。 |
| 19 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 20 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 21 | <code>class&nbsp;JsonApiHandler(BaseHTTPRequestHandler):</code> | 定義 API request handler；每個 HTTP 請求會由這個類別處理。 |
| 22 | <code>&nbsp;&nbsp;&nbsp;&nbsp;repository:&nbsp;RisRepository</code> | 宣告 class attribute repository，稍後由 create_handler 注入 RisRepository 實例。 |
| 23 | <code>&nbsp;&nbsp;&nbsp;&nbsp;default_limit:&nbsp;int</code> | 宣告預設分頁筆數 default_limit。 |
| 24 | <code>&nbsp;&nbsp;&nbsp;&nbsp;max_limit:&nbsp;int</code> | 宣告最大分頁筆數 max_limit。 |
| 25 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 26 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;do_GET(self)&nbsp;-&gt;&nbsp;None:&nbsp;&nbsp;#&nbsp;noqa:&nbsp;N802&nbsp;-&nbsp;required&nbsp;by&nbsp;BaseHTTPRequestHandler</code> | 定義 GET 請求處理方法；BaseHTTPRequestHandler 要求方法名稱必須是 do_GET。 |
| 27 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;parsed&nbsp;=&nbsp;urlparse(self.path)</code> | 解析目前請求路徑 self.path，例如 /records?limit=20。 |
| 28 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;path&nbsp;=&nbsp;parsed.path.rstrip(&quot;/&quot;)&nbsp;or&nbsp;&quot;/&quot;</code> | 取得純路徑並去掉尾端斜線；若結果為空就視為根路徑 /。 |
| 29 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;query&nbsp;=&nbsp;self._flatten_query(parse_qs(parsed.query))</code> | 把 query string 解析並攤平成 Dict[str, str]，方便後續讀參數。 |
| 30 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 31 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;try:</code> | 開始主處理流程的 try 區塊，用來集中捕捉 API 例外。 |
| 32 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;path&nbsp;==&nbsp;&quot;/&quot;&nbsp;or&nbsp;path&nbsp;==&nbsp;&quot;/health&quot;:</code> | 判斷是否打到根路徑 / 或健康檢查 /health。 |
| 33 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self._send_json(HTTPStatus.OK,&nbsp;self.repository.health())</code> | 呼叫 repository.health() 查 DB 狀態，並以 HTTP 200 回傳 JSON。 |
| 34 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return</code> | 健康檢查已處理完成，直接結束本次請求。 |
| 35 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 36 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;path&nbsp;==&nbsp;&quot;/records&quot;:</code> | 判斷是否查詢多筆門牌資料 /records。 |
| 37 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;limit&nbsp;=&nbsp;self._read_int(query,&nbsp;&quot;limit&quot;,&nbsp;self.default_limit,&nbsp;1,&nbsp;self.max_limit)</code> | 讀取 limit 參數；若沒給則用 default_limit，並限制在 1 到 max_limit。 |
| 38 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;offset&nbsp;=&nbsp;self._read_int(query,&nbsp;&quot;offset&quot;,&nbsp;0,&nbsp;0,&nbsp;10_000_000)</code> | 讀取 offset 參數；若沒給則為 0，並限制在 0 到 10,000,000。 |
| 39 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;data&nbsp;=&nbsp;self.repository.list_records(query,&nbsp;limit=limit,&nbsp;offset=offset)</code> | 呼叫 repository.list_records() 依查詢參數、limit、offset 取得資料。 |
| 40 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self._send_json(HTTPStatus.OK,&nbsp;data)</code> | 將查詢結果以 HTTP 200 JSON 回傳。 |
| 41 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return</code> | 多筆資料查詢已處理完成，結束本次請求。 |
| 42 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 43 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;record_match&nbsp;=&nbsp;re.fullmatch(r&quot;/records/(\d+)&quot;,&nbsp;path)</code> | 用正規表示式比對 /records/數字，判斷是否查單筆資料。 |
| 44 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;record_match:</code> | 如果路徑符合 /records/{id}，進入單筆查詢流程。 |
| 45 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;record_id&nbsp;=&nbsp;int(record_match.group(1))</code> | 取出 URL 裡的 id 字串並轉成整數。 |
| 46 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;record&nbsp;=&nbsp;self.repository.get_record(record_id)</code> | 呼叫 repository.get_record() 從資料庫查單筆門牌資料。 |
| 47 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;record&nbsp;is&nbsp;None:</code> | 判斷資料庫是否查無資料。 |
| 48 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self._send_json(HTTPStatus.NOT_FOUND,&nbsp;{&quot;error&quot;:&nbsp;&quot;record_not_found&quot;})</code> | 查無資料時，以 HTTP 404 回傳 record_not_found。 |
| 49 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return</code> | 404 已回覆，結束本次請求。 |
| 50 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self._send_json(HTTPStatus.OK,&nbsp;record)</code> | 查到資料時，以 HTTP 200 回傳該筆 record。 |
| 51 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return</code> | 單筆查詢已處理完成，結束本次請求。 |
| 52 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 53 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;path&nbsp;==&nbsp;&quot;/jobs&quot;:</code> | 判斷是否查詢爬蟲任務紀錄 /jobs。 |
| 54 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;limit&nbsp;=&nbsp;self._read_int(query,&nbsp;&quot;limit&quot;,&nbsp;self.default_limit,&nbsp;1,&nbsp;self.max_limit)</code> | 讀取 jobs API 的 limit 參數。 |
| 55 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;offset&nbsp;=&nbsp;self._read_int(query,&nbsp;&quot;offset&quot;,&nbsp;0,&nbsp;0,&nbsp;10_000_000)</code> | 讀取 jobs API 的 offset 參數。 |
| 56 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status&nbsp;=&nbsp;query.get(&quot;status&quot;,&nbsp;&quot;&quot;)</code> | 讀取可選的 status 參數，例如 success 或 failed。 |
| 57 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;data&nbsp;=&nbsp;self.repository.list_jobs(status=status,&nbsp;limit=limit,&nbsp;offset=offset)</code> | 呼叫 repository.list_jobs() 查詢爬蟲任務紀錄。 |
| 58 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self._send_json(HTTPStatus.OK,&nbsp;data)</code> | 將 jobs 查詢結果以 HTTP 200 JSON 回傳。 |
| 59 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return</code> | jobs 查詢已處理完成，結束本次請求。 |
| 60 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 61 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self._send_json(HTTPStatus.NOT_FOUND,&nbsp;{&quot;error&quot;:&nbsp;&quot;endpoint_not_found&quot;})</code> | 所有已知 endpoint 都不符合時，以 HTTP 404 回傳 endpoint_not_found。 |
| 62 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;except&nbsp;DatabaseNotReadyError&nbsp;as&nbsp;exc:</code> | 捕捉資料庫尚未建立或找不到的例外。 |
| 63 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self._send_json(HTTPStatus.SERVICE_UNAVAILABLE,&nbsp;{&quot;error&quot;:&nbsp;&quot;database_not_ready&quot;,&nbsp;&quot;message&quot;:&nbsp;str(exc)})</code> | 資料庫未就緒時，以 HTTP 503 回傳錯誤訊息。 |
| 64 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;except&nbsp;ValueError&nbsp;as&nbsp;exc:</code> | 捕捉參數格式或範圍錯誤，例如 limit 不是整數。 |
| 65 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self._send_json(HTTPStatus.BAD_REQUEST,&nbsp;{&quot;error&quot;:&nbsp;&quot;bad_request&quot;,&nbsp;&quot;message&quot;:&nbsp;str(exc)})</code> | 參數錯誤時，以 HTTP 400 回傳 bad_request。 |
| 66 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;except&nbsp;Exception&nbsp;as&nbsp;exc:</code> | 捕捉其他未預期例外，避免 server 直接崩潰。 |
| 67 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR,&nbsp;{&quot;error&quot;:&nbsp;&quot;internal_error&quot;,&nbsp;&quot;message&quot;:&nbsp;str(exc)})</code> | 未預期錯誤時，以 HTTP 500 回傳 internal_error 與訊息。 |
| 68 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 69 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;log_message(self,&nbsp;format:&nbsp;str,&nbsp;*args:&nbsp;Any)&nbsp;-&gt;&nbsp;None:</code> | 覆寫標準 handler 的 log_message，控制 console log 格式。 |
| 70 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;print(&quot;%s&nbsp;-&nbsp;-&nbsp;[%s]&nbsp;%s&quot;&nbsp;%&nbsp;(self.client_address[0],&nbsp;self.log_date_time_string(),&nbsp;format&nbsp;%&nbsp;args))</code> | 印出 client IP、時間與 request log。 |
| 71 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 72 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;_send_json(self,&nbsp;status:&nbsp;HTTPStatus,&nbsp;payload:&nbsp;Dict[str,&nbsp;Any])&nbsp;-&gt;&nbsp;None:</code> | 定義統一回傳 JSON 的 helper 方法。 |
| 73 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;body&nbsp;=&nbsp;json.dumps(payload,&nbsp;ensure_ascii=False,&nbsp;indent=2).encode(&quot;utf-8&quot;)</code> | 把 payload 轉成 UTF-8 JSON bytes；ensure_ascii=False 讓中文不被跳脫。 |
| 74 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.send_response(status.value)</code> | 寫入 HTTP 狀態碼，例如 200、404、500。 |
| 75 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.send_header(&quot;Content-Type&quot;,&nbsp;&quot;application/json;&nbsp;charset=utf-8&quot;)</code> | 設定 Content-Type 為 JSON 並指定 UTF-8。 |
| 76 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.send_header(&quot;Content-Length&quot;,&nbsp;str(len(body)))</code> | 設定 Content-Length，告訴 client 回應 body 長度。 |
| 77 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.send_header(&quot;Access-Control-Allow-Origin&quot;,&nbsp;&quot;*&quot;)</code> | 設定 CORS 允許任意來源呼叫這個 API。 |
| 78 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.end_headers()</code> | 結束 header 區段，準備寫 body。 |
| 79 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.wfile.write(body)</code> | 把 JSON body 寫到 HTTP response stream。 |
| 80 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 81 | <code>&nbsp;&nbsp;&nbsp;&nbsp;@staticmethod</code> | 宣告下面的方法不依賴 self，可用 class/static 方式呼叫。 |
| 82 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;_flatten_query(raw_query:&nbsp;Dict[str,&nbsp;list[str]])&nbsp;-&gt;&nbsp;Dict[str,&nbsp;str]:</code> | 定義 query string 攤平工具，輸入是 parse_qs 產生的 Dict[str, list[str]]。 |
| 83 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;{key:&nbsp;values[-1]&nbsp;if&nbsp;values&nbsp;else&nbsp;&quot;&quot;&nbsp;for&nbsp;key,&nbsp;values&nbsp;in&nbsp;raw_query.items()}</code> | 每個 query 參數取最後一個值；如果沒有值則給空字串。 |
| 84 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 85 | <code>&nbsp;&nbsp;&nbsp;&nbsp;@staticmethod</code> | 宣告下面的整數讀取方法為 staticmethod。 |
| 86 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;_read_int(query:&nbsp;Dict[str,&nbsp;str],&nbsp;name:&nbsp;str,&nbsp;default:&nbsp;int,&nbsp;min_value:&nbsp;int,&nbsp;max_value:&nbsp;int)&nbsp;-&gt;&nbsp;int:</code> | 定義讀整數 query 參數的共用工具，含預設值與上下限檢查。 |
| 87 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raw_value&nbsp;=&nbsp;query.get(name,&nbsp;&quot;&quot;)</code> | 從 query dict 取出參數原始字串。 |
| 88 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;raw_value&nbsp;==&nbsp;&quot;&quot;:</code> | 判斷使用者是否沒有提供該參數。 |
| 89 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;default</code> | 沒提供時回傳預設值。 |
| 90 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;try:</code> | 開始嘗試把字串轉成整數。 |
| 91 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;value&nbsp;=&nbsp;int(raw_value)</code> | 將 raw_value 轉為 int。 |
| 92 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;except&nbsp;ValueError&nbsp;as&nbsp;exc:</code> | 捕捉無法轉 int 的錯誤。 |
| 93 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise&nbsp;ValueError(f&quot;{name}&nbsp;must&nbsp;be&nbsp;an&nbsp;integer&quot;)&nbsp;from&nbsp;exc</code> | 丟出更清楚的錯誤訊息，讓上層回 HTTP 400。 |
| 94 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;value&nbsp;&lt;&nbsp;min_value&nbsp;or&nbsp;value&nbsp;&gt;&nbsp;max_value:</code> | 檢查整數是否超出允許範圍。 |
| 95 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise&nbsp;ValueError(f&quot;{name}&nbsp;must&nbsp;be&nbsp;between&nbsp;{min_value}&nbsp;and&nbsp;{max_value}&quot;)</code> | 超出範圍時丟出錯誤，提示合法上下限。 |
| 96 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;value</code> | 參數合法時回傳整數值。 |
| 97 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 98 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 99 | <code>def&nbsp;load_config(config_path:&nbsp;Path)&nbsp;-&gt;&nbsp;Dict[str,&nbsp;Any]:</code> | 定義讀取 config JSON 的函式。 |
| 100 | <code>&nbsp;&nbsp;&nbsp;&nbsp;with&nbsp;config_path.open(&quot;r&quot;,&nbsp;encoding=&quot;utf-8-sig&quot;)&nbsp;as&nbsp;f:</code> | 以 utf-8-sig 開啟設定檔，可容忍檔案開頭 BOM。 |
| 101 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;json.load(f)</code> | 把 JSON 檔轉成 Python dict 並回傳。 |
| 102 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 103 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 104 | <code>def&nbsp;create_handler(config:&nbsp;Dict[str,&nbsp;Any],&nbsp;config_path:&nbsp;Path)&nbsp;-&gt;&nbsp;type[JsonApiHandler]:</code> | 定義建立 handler class 的工廠函式，用 config 注入資料庫與分頁設定。 |
| 105 | <code>&nbsp;&nbsp;&nbsp;&nbsp;database_path&nbsp;=&nbsp;Path(config[&quot;database_path&quot;])</code> | 從 config 讀 database_path 並轉成 Path 物件。 |
| 106 | <code>&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;not&nbsp;database_path.is_absolute():</code> | 判斷 database_path 是否不是絕對路徑。 |
| 107 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;database_path&nbsp;=&nbsp;(config_path.parent&nbsp;/&nbsp;database_path).resolve()</code> | 若是相對路徑，就以 config 檔所在資料夾為基準解析成絕對路徑。 |
| 108 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 109 | <code>&nbsp;&nbsp;&nbsp;&nbsp;class&nbsp;ConfiguredHandler(JsonApiHandler):</code> | 在函式內定義 ConfiguredHandler，繼承 JsonApiHandler 並綁定設定。 |
| 110 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;repository&nbsp;=&nbsp;RisRepository(database_path)</code> | 建立 RisRepository 實例，指定要讀取的 SQLite 資料庫。 |
| 111 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;default_limit&nbsp;=&nbsp;int(config.get(&quot;default_limit&quot;,&nbsp;50))</code> | 從 config 讀 default_limit，沒設定就用 50。 |
| 112 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;max_limit&nbsp;=&nbsp;int(config.get(&quot;max_limit&quot;,&nbsp;500))</code> | 從 config 讀 max_limit，沒設定就用 500。 |
| 113 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 114 | <code>&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;ConfiguredHandler</code> | 回傳已經綁定 repository 與分頁設定的 handler class。 |
| 115 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 116 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 117 | <code>def&nbsp;parse_args()&nbsp;-&gt;&nbsp;argparse.Namespace:</code> | 定義解析命令列參數的函式。 |
| 118 | <code>&nbsp;&nbsp;&nbsp;&nbsp;parser&nbsp;=&nbsp;argparse.ArgumentParser(description=&quot;RIS&nbsp;3053&nbsp;API&nbsp;service&quot;)</code> | 建立 ArgumentParser，設定 CLI 說明文字。 |
| 119 | <code>&nbsp;&nbsp;&nbsp;&nbsp;parser.add_argument(&quot;--config&quot;,&nbsp;default=&quot;config.json&quot;,&nbsp;help=&quot;Path&nbsp;to&nbsp;config&nbsp;JSON&quot;)</code> | 新增 --config 參數，可指定 config JSON 路徑，預設 config.json。 |
| 120 | <code>&nbsp;&nbsp;&nbsp;&nbsp;parser.add_argument(&quot;--host&quot;,&nbsp;help=&quot;Override&nbsp;host&nbsp;from&nbsp;config&quot;)</code> | 新增 --host 參數，可覆蓋 config 裡的 host。 |
| 121 | <code>&nbsp;&nbsp;&nbsp;&nbsp;parser.add_argument(&quot;--port&quot;,&nbsp;type=int,&nbsp;help=&quot;Override&nbsp;port&nbsp;from&nbsp;config&quot;)</code> | 新增 --port 參數，可覆蓋 config 裡的 port，並轉成 int。 |
| 122 | <code>&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;parser.parse_args()</code> | 解析命令列參數並回傳 Namespace。 |
| 123 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 124 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 125 | <code>def&nbsp;main()&nbsp;-&gt;&nbsp;int:</code> | 定義主程式入口，回傳整數 exit code。 |
| 126 | <code>&nbsp;&nbsp;&nbsp;&nbsp;args&nbsp;=&nbsp;parse_args()</code> | 解析 CLI 參數。 |
| 127 | <code>&nbsp;&nbsp;&nbsp;&nbsp;config_path&nbsp;=&nbsp;Path(args.config).resolve()</code> | 把 config 路徑轉成絕對路徑。 |
| 128 | <code>&nbsp;&nbsp;&nbsp;&nbsp;config&nbsp;=&nbsp;load_config(config_path)</code> | 讀取 config JSON。 |
| 129 | <code>&nbsp;&nbsp;&nbsp;&nbsp;host&nbsp;=&nbsp;args.host&nbsp;or&nbsp;config.get(&quot;host&quot;,&nbsp;&quot;127.0.0.1&quot;)</code> | 決定 server 綁定 host：命令列優先，否則用 config，最後預設 127.0.0.1。 |
| 130 | <code>&nbsp;&nbsp;&nbsp;&nbsp;port&nbsp;=&nbsp;args.port&nbsp;or&nbsp;int(config.get(&quot;port&quot;,&nbsp;8000))</code> | 決定 port：命令列優先，否則用 config，最後預設 8000。 |
| 131 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 132 | <code>&nbsp;&nbsp;&nbsp;&nbsp;handler_class&nbsp;=&nbsp;create_handler(config,&nbsp;config_path)</code> | 建立綁定 config 的 request handler class。 |
| 133 | <code>&nbsp;&nbsp;&nbsp;&nbsp;server&nbsp;=&nbsp;ThreadingHTTPServer((host,&nbsp;port),&nbsp;handler_class)</code> | 建立多執行緒 HTTP server，監聽指定 host 與 port。 |
| 134 | <code>&nbsp;&nbsp;&nbsp;&nbsp;print(f&quot;RIS&nbsp;API&nbsp;service&nbsp;running&nbsp;at&nbsp;http://{host}:{port}&quot;)</code> | 在 console 印出服務 URL。 |
| 135 | <code>&nbsp;&nbsp;&nbsp;&nbsp;print(&quot;Press&nbsp;Ctrl+C&nbsp;to&nbsp;stop.&quot;)</code> | 提示使用者可按 Ctrl+C 停止服務。 |
| 136 | <code>&nbsp;&nbsp;&nbsp;&nbsp;try:</code> | 開始 server 執行的 try 區塊。 |
| 137 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;server.serve_forever()</code> | 讓 HTTP server 持續服務請求直到被停止。 |
| 138 | <code>&nbsp;&nbsp;&nbsp;&nbsp;except&nbsp;KeyboardInterrupt:</code> | 捕捉 Ctrl+C 造成的 KeyboardInterrupt。 |
| 139 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;print(&quot;\nStopping&nbsp;API&nbsp;service...&quot;)</code> | 收到停止訊號時印出停止訊息。 |
| 140 | <code>&nbsp;&nbsp;&nbsp;&nbsp;finally:</code> | finally 區塊，不論是否例外都會執行清理。 |
| 141 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;server.server_close()</code> | 關閉 server socket，釋放 port。 |
| 142 | <code>&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;0</code> | 主程式正常結束，回傳 exit code 0。 |
| 143 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 144 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 145 | <code>if&nbsp;__name__&nbsp;==&nbsp;&quot;__main__&quot;:</code> | 判斷此檔案是否被直接執行，而不是被其他檔 import。 |
| 146 | <code>&nbsp;&nbsp;&nbsp;&nbsp;raise&nbsp;SystemExit(main())</code> | 直接執行時呼叫 main()，並用 SystemExit 回傳 exit code。 |

## `repository.py` 逐行說明
| 行號 | 原始碼 | 說明 |
| ---: | --- | --- |
| 1 | <code>&quot;&quot;&quot;SQLite&nbsp;data&nbsp;access&nbsp;layer&nbsp;for&nbsp;RIS&nbsp;API&nbsp;service.&quot;&quot;&quot;</code> | 模組說明字串，表示此檔是 RIS API 的 SQLite 資料存取層。 |
| 2 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 3 | <code>from&nbsp;__future__&nbsp;import&nbsp;annotations</code> | 啟用延後解析型別註解。 |
| 4 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 5 | <code>import&nbsp;sqlite3</code> | 匯入 sqlite3 標準庫，用來連線與查詢 SQLite。 |
| 6 | <code>from&nbsp;pathlib&nbsp;import&nbsp;Path</code> | 匯入 Path，用來保存資料庫檔案路徑。 |
| 7 | <code>from&nbsp;typing&nbsp;import&nbsp;Any,&nbsp;Dict,&nbsp;List,&nbsp;Tuple</code> | 匯入型別提示 Any、Dict、List、Tuple。 |
| 8 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 9 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 10 | <code>class&nbsp;DatabaseNotReadyError(RuntimeError):</code> | 定義自訂例外，代表爬蟲資料庫尚未建立或不可用。 |
| 11 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&quot;&quot;&quot;Raised&nbsp;when&nbsp;the&nbsp;crawler&nbsp;database&nbsp;has&nbsp;not&nbsp;been&nbsp;created&nbsp;yet.&quot;&quot;&quot;</code> | 例外類別的說明字串。 |
| 12 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 13 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 14 | <code>class&nbsp;RisRepository:</code> | 定義 RisRepository，集中管理所有資料庫查詢邏輯。 |
| 15 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;__init__(self,&nbsp;database_path:&nbsp;Path)&nbsp;-&gt;&nbsp;None:</code> | 建構子，建立 repository 時需要傳入 database_path。 |
| 16 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;self.database_path&nbsp;=&nbsp;database_path</code> | 把資料庫路徑存成物件屬性，供其他方法使用。 |
| 17 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 18 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;health(self)&nbsp;-&gt;&nbsp;Dict[str,&nbsp;Any]:</code> | 定義健康檢查方法，回傳資料庫存在狀態與資料筆數。 |
| 19 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;exists&nbsp;=&nbsp;self.database_path.exists()</code> | 檢查 SQLite 檔案是否存在。 |
| 20 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;not&nbsp;exists:</code> | 如果資料庫檔案不存在，進入未就緒回傳流程。 |
| 21 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;{</code> | 開始組裝 health API 的回傳 dict。 |
| 22 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;ok&quot;:&nbsp;False,</code> | ok 為 False，表示服務資料來源尚未可用。 |
| 23 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;database_exists&quot;:&nbsp;False,</code> | database_exists 為 False，明確表示 DB 檔不存在。 |
| 24 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;database_path&quot;:&nbsp;str(self.database_path),</code> | 回傳目前預期的資料庫路徑，方便排查設定。 |
| 25 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;record_count&quot;:&nbsp;0,</code> | 資料庫不存在時，門牌資料筆數視為 0。 |
| 26 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;job_count&quot;:&nbsp;0,</code> | 資料庫不存在時，爬蟲任務筆數視為 0。 |
| 27 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</code> | 結束未就緒狀態的回傳 dict。 |
| 28 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 29 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with&nbsp;self._connect()&nbsp;as&nbsp;conn:</code> | 資料庫存在時，開啟 SQLite 連線並在區塊結束自動關閉。 |
| 30 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;{</code> | 開始組裝資料庫可用時的 health 回傳 dict。 |
| 31 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;ok&quot;:&nbsp;True,</code> | ok 為 True，表示資料庫存在且可查詢。 |
| 32 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;database_exists&quot;:&nbsp;True,</code> | database_exists 為 True。 |
| 33 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;database_path&quot;:&nbsp;str(self.database_path),</code> | 回傳資料庫實際路徑。 |
| 34 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;record_count&quot;:&nbsp;self._count_table(conn,&nbsp;&quot;doorplate_record&quot;),</code> | 統計 doorplate_record 表的資料筆數。 |
| 35 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;job_count&quot;:&nbsp;self._count_table(conn,&nbsp;&quot;crawl_job&quot;),</code> | 統計 crawl_job 表的資料筆數。 |
| 36 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</code> | 結束健康檢查回傳 dict。 |
| 37 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 38 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;list_records(self,&nbsp;filters:&nbsp;Dict[str,&nbsp;str],&nbsp;limit:&nbsp;int,&nbsp;offset:&nbsp;int)&nbsp;-&gt;&nbsp;Dict[str,&nbsp;Any]:</code> | 定義多筆門牌資料查詢方法，接收 filters、limit、offset。 |
| 39 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;where_sql,&nbsp;params&nbsp;=&nbsp;self._build_record_where(filters)</code> | 依 API filters 建立 SQL WHERE 子句與參數陣列。 |
| 40 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;sql&nbsp;=&nbsp;f&quot;&quot;&quot;</code> | 開始組裝查詢門牌資料的 SQL 字串。 |
| 41 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;SELECT</code> | SQL SELECT 開頭，表示要查詢欄位。 |
| 42 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;id,</code> | 查詢 id 欄位。 |
| 43 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;city_code,</code> | 查詢 city_code 縣市代碼。 |
| 44 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;area_code,</code> | 查詢 area_code 鄉鎮市區代碼。 |
| 45 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;address_text,</code> | 查詢 address_text 門牌地址文字。 |
| 46 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;register_date,</code> | 查詢 register_date 編釘日期。 |
| 47 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;register_kind_code,</code> | 查詢 register_kind_code 編釘類別代碼。 |
| 48 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;register_kind_name,</code> | 查詢 register_kind_name 編釘類別名稱。 |
| 49 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raw_file_path,</code> | 查詢 raw_file_path 原始 JSON 檔案路徑。 |
| 50 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;first_seen_at,</code> | 查詢 first_seen_at 第一次入庫時間。 |
| 51 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;last_seen_at</code> | 查詢 last_seen_at 最近一次看到/更新時間。 |
| 52 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;FROM&nbsp;doorplate_record</code> | 指定資料來源表 doorplate_record。 |
| 53 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{where_sql}</code> | 插入動態 WHERE 條件；若無條件則為空字串。 |
| 54 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ORDER&nbsp;BY&nbsp;id&nbsp;DESC</code> | 依 id 由新到舊排序。 |
| 55 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;LIMIT&nbsp;?&nbsp;OFFSET&nbsp;?</code> | 加入分頁限制 LIMIT 與 OFFSET，使用參數化查詢避免 SQL injection。 |
| 56 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;&quot;&quot;</code> | SQL 字串結束。 |
| 57 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;count_sql&nbsp;=&nbsp;f&quot;SELECT&nbsp;COUNT(*)&nbsp;AS&nbsp;total&nbsp;FROM&nbsp;doorplate_record&nbsp;{where_sql}&quot;</code> | 建立統計總筆數的 SQL，用同一組 WHERE 條件。 |
| 58 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 59 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with&nbsp;self._connect()&nbsp;as&nbsp;conn:</code> | 開啟資料庫連線。 |
| 60 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;total&nbsp;=&nbsp;conn.execute(count_sql,&nbsp;params).fetchone()[&quot;total&quot;]</code> | 執行 count_sql 取得符合條件的總筆數。 |
| 61 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;rows&nbsp;=&nbsp;conn.execute(sql,&nbsp;params&nbsp;+&nbsp;[limit,&nbsp;offset]).fetchall()</code> | 執行列表 SQL，並把 limit、offset 加到查詢參數後面。 |
| 62 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;{</code> | 開始組裝 API 回傳 dict。 |
| 63 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;total&quot;:&nbsp;total,</code> | 回傳符合條件的總筆數。 |
| 64 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;limit&quot;:&nbsp;limit,</code> | 回傳本次使用的 limit。 |
| 65 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;offset&quot;:&nbsp;offset,</code> | 回傳本次使用的 offset。 |
| 66 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;items&quot;:&nbsp;[dict(row)&nbsp;for&nbsp;row&nbsp;in&nbsp;rows],</code> | 把 sqlite3.Row 逐筆轉成 dict，作為 items 陣列。 |
| 67 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</code> | 結束 list_records 回傳 dict。 |
| 68 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 69 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;get_record(self,&nbsp;record_id:&nbsp;int)&nbsp;-&gt;&nbsp;Dict[str,&nbsp;Any]&nbsp;&#124;&nbsp;None:</code> | 定義查單筆門牌資料方法；找不到時回傳 None。 |
| 70 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;sql&nbsp;=&nbsp;&quot;&quot;&quot;</code> | 開始組裝單筆查詢 SQL。 |
| 71 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;SELECT</code> | SQL SELECT 開頭。 |
| 72 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;id,</code> | 查詢 id。 |
| 73 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;city_code,</code> | 查詢 city_code。 |
| 74 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;area_code,</code> | 查詢 area_code。 |
| 75 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;address_text,</code> | 查詢 address_text。 |
| 76 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;register_date,</code> | 查詢 register_date。 |
| 77 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;register_kind_code,</code> | 查詢 register_kind_code。 |
| 78 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;register_kind_name,</code> | 查詢 register_kind_name。 |
| 79 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;source_hash,</code> | 查詢 source_hash，用於資料去重識別。 |
| 80 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raw_file_path,</code> | 查詢 raw_file_path。 |
| 81 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;first_seen_at,</code> | 查詢 first_seen_at。 |
| 82 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;last_seen_at</code> | 查詢 last_seen_at。 |
| 83 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;FROM&nbsp;doorplate_record</code> | 指定來源表 doorplate_record。 |
| 84 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;WHERE&nbsp;id&nbsp;=&nbsp;?</code> | 限制只查 id 等於指定參數的資料。 |
| 85 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;&quot;&quot;</code> | SQL 字串結束。 |
| 86 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with&nbsp;self._connect()&nbsp;as&nbsp;conn:</code> | 開啟資料庫連線。 |
| 87 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;row&nbsp;=&nbsp;conn.execute(sql,&nbsp;[record_id]).fetchone()</code> | 用參數化查詢執行單筆查詢並取第一筆。 |
| 88 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;dict(row)&nbsp;if&nbsp;row&nbsp;else&nbsp;None</code> | 若有資料轉成 dict，否則回傳 None。 |
| 89 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 90 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;list_jobs(self,&nbsp;status:&nbsp;str,&nbsp;limit:&nbsp;int,&nbsp;offset:&nbsp;int)&nbsp;-&gt;&nbsp;Dict[str,&nbsp;Any]:</code> | 定義爬蟲任務紀錄查詢方法，可依 status 過濾並分頁。 |
| 91 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;params:&nbsp;List[Any]&nbsp;=&nbsp;[]</code> | 建立 SQL 參數陣列。 |
| 92 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;where_sql&nbsp;=&nbsp;&quot;&quot;</code> | 預設沒有 WHERE 條件。 |
| 93 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;status:</code> | 如果呼叫端有提供 status，才加狀態過濾。 |
| 94 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;where_sql&nbsp;=&nbsp;&quot;WHERE&nbsp;status&nbsp;=&nbsp;?&quot;</code> | 設定 WHERE 子句為 status = ?。 |
| 95 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;params.append(status)</code> | 把 status 加入參數陣列。 |
| 96 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 97 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;sql&nbsp;=&nbsp;f&quot;&quot;&quot;</code> | 開始組裝 jobs 查詢 SQL。 |
| 98 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;SELECT</code> | SQL SELECT 開頭。 |
| 99 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;id,</code> | 查詢 job id。 |
| 100 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;job_key,</code> | 查詢 job_key，代表唯一任務鍵。 |
| 101 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;query_name,</code> | 查詢 query_name。 |
| 102 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;city_code,</code> | 查詢 city_code。 |
| 103 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;area_code,</code> | 查詢 area_code。 |
| 104 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;register_kind,</code> | 查詢 register_kind。 |
| 105 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;s_date,</code> | 查詢起始日期 s_date。 |
| 106 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;e_date,</code> | 查詢結束日期 e_date。 |
| 107 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;page,</code> | 查詢頁碼 page。 |
| 108 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;status,</code> | 查詢任務狀態 status。 |
| 109 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raw_file_path,</code> | 查詢 raw_file_path。 |
| 110 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;row_count,</code> | 查詢 row_count，本頁入庫筆數。 |
| 111 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;error_message,</code> | 查詢 error_message。 |
| 112 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;started_at,</code> | 查詢 started_at。 |
| 113 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;finished_at,</code> | 查詢 finished_at。 |
| 114 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;created_at</code> | 查詢 created_at。 |
| 115 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;FROM&nbsp;crawl_job</code> | 指定來源表 crawl_job。 |
| 116 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{where_sql}</code> | 插入可選的 WHERE 條件。 |
| 117 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ORDER&nbsp;BY&nbsp;id&nbsp;DESC</code> | 依 id 由新到舊排序。 |
| 118 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;LIMIT&nbsp;?&nbsp;OFFSET&nbsp;?</code> | 加入 LIMIT/OFFSET 分頁。 |
| 119 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;&quot;&quot;</code> | SQL 字串結束。 |
| 120 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;count_sql&nbsp;=&nbsp;f&quot;SELECT&nbsp;COUNT(*)&nbsp;AS&nbsp;total&nbsp;FROM&nbsp;crawl_job&nbsp;{where_sql}&quot;</code> | 建立統計 crawl_job 總筆數的 SQL。 |
| 121 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 122 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;with&nbsp;self._connect()&nbsp;as&nbsp;conn:</code> | 開啟資料庫連線。 |
| 123 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;total&nbsp;=&nbsp;conn.execute(count_sql,&nbsp;params).fetchone()[&quot;total&quot;]</code> | 執行 count_sql 取得符合條件的 jobs 總筆數。 |
| 124 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;rows&nbsp;=&nbsp;conn.execute(sql,&nbsp;params&nbsp;+&nbsp;[limit,&nbsp;offset]).fetchall()</code> | 執行 jobs 列表查詢，附加 limit 與 offset 參數。 |
| 125 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;{</code> | 開始組裝 jobs API 回傳 dict。 |
| 126 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;total&quot;:&nbsp;total,</code> | 回傳總筆數。 |
| 127 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;limit&quot;:&nbsp;limit,</code> | 回傳 limit。 |
| 128 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;offset&quot;:&nbsp;offset,</code> | 回傳 offset。 |
| 129 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;items&quot;:&nbsp;[dict(row)&nbsp;for&nbsp;row&nbsp;in&nbsp;rows],</code> | 把每筆 sqlite3.Row 轉成 dict 放進 items。 |
| 130 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</code> | 結束 list_jobs 回傳 dict。 |
| 131 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 132 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;_connect(self)&nbsp;-&gt;&nbsp;sqlite3.Connection:</code> | 定義內部連線方法，統一處理 DB 是否存在與 row_factory。 |
| 133 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;not&nbsp;self.database_path.exists():</code> | 檢查資料庫檔案是否存在。 |
| 134 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;raise&nbsp;DatabaseNotReadyError(</code> | 不存在時丟出 DatabaseNotReadyError。 |
| 135 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;f&quot;Database&nbsp;not&nbsp;found:&nbsp;{self.database_path}.&nbsp;Run&nbsp;the&nbsp;crawler&nbsp;first.&quot;</code> | 錯誤訊息內容，提示要先執行 crawler。 |
| 136 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;)</code> | 結束 raise 區塊。 |
| 137 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;conn&nbsp;=&nbsp;sqlite3.connect(self.database_path)</code> | 建立 SQLite 連線。 |
| 138 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;conn.row_factory&nbsp;=&nbsp;sqlite3.Row</code> | 設定 row_factory 為 sqlite3.Row，讓查詢結果可用欄位名稱取值。 |
| 139 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;conn</code> | 回傳連線物件。 |
| 140 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 141 | <code>&nbsp;&nbsp;&nbsp;&nbsp;@staticmethod</code> | 宣告下面的 count 方法不依賴 self。 |
| 142 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;_count_table(conn:&nbsp;sqlite3.Connection,&nbsp;table_name:&nbsp;str)&nbsp;-&gt;&nbsp;int:</code> | 定義統計指定資料表筆數的方法。 |
| 143 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;try:</code> | 開始 try，避免資料表不存在時健康檢查失敗。 |
| 144 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;int(conn.execute(f&quot;SELECT&nbsp;COUNT(*)&nbsp;AS&nbsp;total&nbsp;FROM&nbsp;{table_name}&quot;).fetchone()[&quot;total&quot;])</code> | 執行 SELECT COUNT(*) 並回傳整數總筆數。 |
| 145 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;except&nbsp;sqlite3.Error:</code> | 捕捉 SQLite 錯誤，例如資料表不存在。 |
| 146 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;0</code> | 發生錯誤時回傳 0，讓 /health 仍可回應。 |
| 147 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 148 | <code>&nbsp;&nbsp;&nbsp;&nbsp;@staticmethod</code> | 宣告 WHERE builder 為 staticmethod。 |
| 149 | <code>&nbsp;&nbsp;&nbsp;&nbsp;def&nbsp;_build_record_where(filters:&nbsp;Dict[str,&nbsp;str])&nbsp;-&gt;&nbsp;Tuple[str,&nbsp;List[Any]]:</code> | 定義根據 API filters 建立 WHERE SQL 與參數的方法。 |
| 150 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;clauses:&nbsp;List[str]&nbsp;=&nbsp;[]</code> | 建立 WHERE 條件字串陣列。 |
| 151 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;params:&nbsp;List[Any]&nbsp;=&nbsp;[]</code> | 建立對應 SQL ? 佔位符的參數陣列。 |
| 152 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 153 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;exact_fields&nbsp;=&nbsp;{</code> | 建立 API 查詢參數名稱到資料庫欄位名稱的對照表。 |
| 154 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;cityCode&quot;:&nbsp;&quot;city_code&quot;,</code> | cityCode 對應資料庫 city_code。 |
| 155 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;areaCode&quot;:&nbsp;&quot;area_code&quot;,</code> | areaCode 對應資料庫 area_code。 |
| 156 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&quot;registerKind&quot;:&nbsp;&quot;register_kind_code&quot;,</code> | registerKind 對應資料庫 register_kind_code。 |
| 157 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;}</code> | 對照表結束。 |
| 158 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;for&nbsp;query_name,&nbsp;column_name&nbsp;in&nbsp;exact_fields.items():</code> | 逐一處理 exact_fields 中的查詢參數。 |
| 159 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;value&nbsp;=&nbsp;filters.get(query_name,&nbsp;&quot;&quot;).strip()</code> | 從 filters 取值並 strip 去掉前後空白。 |
| 160 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;value:</code> | 如果使用者有提供值，才加入條件。 |
| 161 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;clauses.append(f&quot;{column_name}&nbsp;=&nbsp;?&quot;)</code> | 加入等值查詢條件，例如 city_code = ?。 |
| 162 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;params.append(value)</code> | 把實際查詢值加入參數陣列。 |
| 163 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 164 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;date_from&nbsp;=&nbsp;filters.get(&quot;dateFrom&quot;,&nbsp;&quot;&quot;).strip()</code> | 讀取 dateFrom 參數。 |
| 165 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;date_from:</code> | 如果有 dateFrom，加入起始日期條件。 |
| 166 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;clauses.append(&quot;register_date&nbsp;&gt;=&nbsp;?&quot;)</code> | 加入 register_date >= ? 條件。 |
| 167 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;params.append(date_from)</code> | 把 dateFrom 值加入參數陣列。 |
| 168 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 169 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;date_to&nbsp;=&nbsp;filters.get(&quot;dateTo&quot;,&nbsp;&quot;&quot;).strip()</code> | 讀取 dateTo 參數。 |
| 170 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;date_to:</code> | 如果有 dateTo，加入結束日期條件。 |
| 171 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;clauses.append(&quot;register_date&nbsp;&lt;=&nbsp;?&quot;)</code> | 加入 register_date <= ? 條件。 |
| 172 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;params.append(date_to)</code> | 把 dateTo 值加入參數陣列。 |
| 173 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 174 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;keyword&nbsp;=&nbsp;filters.get(&quot;q&quot;,&nbsp;&quot;&quot;).strip()</code> | 讀取 q 地址關鍵字參數。 |
| 175 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;keyword:</code> | 如果有 keyword，加入模糊查詢條件。 |
| 176 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;clauses.append(&quot;address_text&nbsp;LIKE&nbsp;?&quot;)</code> | 加入 address_text LIKE ? 條件。 |
| 177 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;params.append(f&quot;%{keyword}%&quot;)</code> | 把 keyword 包成 %keyword%，表示地址中包含該字串即可。 |
| 178 | （空行） | 空行，用來分隔區塊、提升可讀性。 |
| 179 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if&nbsp;not&nbsp;clauses:</code> | 如果沒有任何查詢條件，回傳空 WHERE。 |
| 180 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;&quot;&quot;,&nbsp;params</code> | 回傳空字串與目前參數陣列。 |
| 181 | <code>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return&nbsp;&quot;WHERE&nbsp;&quot;&nbsp;+&nbsp;&quot;&nbsp;AND&nbsp;&quot;.join(clauses),&nbsp;params</code> | 有條件時，把所有條件用 AND 串起來並加上 WHERE。 |

## `config.json` 逐行說明
| 行號 | 原始碼 | 說明 |
| ---: | --- | --- |
| 1 | <code>{</code> | JSON 設定檔開頭。 |
| 2 | <code>&nbsp;&nbsp;&quot;host&quot;:&nbsp;&quot;127.0.0.1&quot;,</code> | API server 綁定的 host；127.0.0.1 代表只允許本機連線。 |
| 3 | <code>&nbsp;&nbsp;&quot;port&quot;:&nbsp;8000,</code> | API server 預設監聽 port 8000。 |
| 4 | <code>&nbsp;&nbsp;&quot;database_path&quot;:&nbsp;&quot;../ris_crawler_3053/data/ris_doorplate.sqlite3&quot;,</code> | 爬蟲產生的 SQLite 資料庫位置；相對於 API 專案資料夾。 |
| 5 | <code>&nbsp;&nbsp;&quot;default_limit&quot;:&nbsp;50,</code> | 列表 API 預設回傳筆數。 |
| 6 | <code>&nbsp;&nbsp;&quot;max_limit&quot;:&nbsp;500</code> | 列表 API 允許的最大回傳筆數，避免一次查太多資料。 |
| 7 | <code>}</code> | JSON 設定檔結尾。 |

## 執行方式提醒
```powershell
cd C:\Users\user\ris_api_service_3053
python main.py
```
啟動後可用 `http://127.0.0.1:8000/health` 確認 API 與資料庫狀態。
