"""
内置函数/方法可控性知识库

为静态分析引擎提供语言内置函数的返回值可控性信息，避免对已知函数进行不必要的函数体分析。

知识条目结构:
    {函数名: {"passthrough": [参数位置列表], "safe": bool}}

    - passthrough: 返回值依赖哪些参数的位置（0-indexed）。
      [] 表示返回值与输入参数无关（如 len() 返回整数）。
    - safe: True 表示该函数做了有效安全过滤，返回值不再构成安全威胁。

使用场景:
    引擎追踪到 a = func(b) 时，先查知识库：
    1. func 在知识库中 + safe=True + passthrough=[] → 返回 code=-1（安全，不可控）
    2. func 在知识库中 + passthrough=[0] → 返回 ('deps', [b的变量名])（透传）
    3. func 不在知识库中 → 正常进入函数体分析（deps 机制）
"""


class BuiltinKnowledge:
    """
    四语言内置函数/方法可控性知识库

    键名格式:
    - 模块函数: "module.func"  如 "html.escape"
    - 类方法:   "Class.method" 如 "str.upper"
    - 全局函数: "func"         如 "trim"
    - 链式方法: "method"       如 "toUpperCase"（JS/Java 链式调用时只有方法名）
    """

    PYTHON = {
        # ===== 字符串方法（透传 self） =====
        "str.upper":        {"passthrough": [0], "safe": False},
        "str.lower":        {"passthrough": [0], "safe": False},
        "str.strip":        {"passthrough": [0], "safe": False},
        "str.lstrip":       {"passthrough": [0], "safe": False},
        "str.rstrip":       {"passthrough": [0], "safe": False},
        "str.capitalize":   {"passthrough": [0], "safe": False},
        "str.title":        {"passthrough": [0], "safe": False},
        "str.swapcase":     {"passthrough": [0], "safe": False},
        "str.replace":      {"passthrough": [0], "safe": False},
        "str.split":        {"passthrough": [0], "safe": False},
        "str.rsplit":       {"passthrough": [0], "safe": False},
        "str.splitlines":   {"passthrough": [0], "safe": False},
        "str.encode":       {"passthrough": [0], "safe": False},
        "str.decode":       {"passthrough": [0], "safe": False},
        "str.format":       {"passthrough": [0], "safe": False},
        "str.join":         {"passthrough": [1], "safe": False},
        "str.center":       {"passthrough": [0], "safe": False},
        "str.ljust":        {"passthrough": [0], "safe": False},
        "str.rjust":        {"passthrough": [0], "safe": False},
        "str.zfill":        {"passthrough": [0], "safe": False},
        "str.expandtabs":   {"passthrough": [0], "safe": False},
        "str.removeprefix": {"passthrough": [0], "safe": False},
        "str.removesuffix": {"passthrough": [0], "safe": False},
        "str.casefold":     {"passthrough": [0], "safe": False},
        "str.translate":    {"passthrough": [0], "safe": False},

        # ===== 内置类型转换（透传参数） =====
        "str":              {"passthrough": [0], "safe": False},
        "int":              {"passthrough": [], "safe": True},   # 返回整数
        "float":            {"passthrough": [], "safe": True},   # 返回浮点数
        "bool":             {"passthrough": [], "safe": True},   # 返回布尔值
        "bytes":            {"passthrough": [0], "safe": False},
        "bytearray":        {"passthrough": [0], "safe": False},
        "list":             {"passthrough": [0], "safe": False},
        "dict":             {"passthrough": [0], "safe": False},
        "tuple":            {"passthrough": [0], "safe": False},
        "set":              {"passthrough": [0], "safe": False},
        "frozenset":        {"passthrough": [0], "safe": False},
        "repr":             {"passthrough": [0], "safe": False},
        "format":           {"passthrough": [0], "safe": False},
        "sorted":           {"passthrough": [0], "safe": False},
        "reversed":         {"passthrough": [0], "safe": False},
        "enumerate":        {"passthrough": [0], "safe": False},
        "zip":              {"passthrough": [0, 1], "safe": False},
        "map":              {"passthrough": [1], "safe": False},
        "filter":           {"passthrough": [1], "safe": False},
        "slice":            {"passthrough": [0], "safe": False},
        "ord":              {"passthrough": [], "safe": True},   # 返回整数
        "chr":              {"passthrough": [], "safe": True},   # 返回单字符
        "hex":              {"passthrough": [], "safe": True},
        "oct":              {"passthrough": [], "safe": True},
        "bin":              {"passthrough": [], "safe": True},

        # ===== 不透传（返回值与输入无关） =====
        "len":              {"passthrough": [], "safe": True},
        "type":             {"passthrough": [], "safe": True},
        "isinstance":       {"passthrough": [], "safe": True},
        "issubclass":       {"passthrough": [], "safe": True},
        "id":               {"passthrough": [], "safe": True},
        "hash":             {"passthrough": [], "safe": True},
        "dir":              {"passthrough": [], "safe": True},
        "vars":             {"passthrough": [], "safe": True},
        "callable":         {"passthrough": [], "safe": True},
        "hasattr":          {"passthrough": [], "safe": True},
        "getattr":          {"passthrough": [0], "safe": False},
        "setattr":          {"passthrough": [], "safe": True},
        "abs":              {"passthrough": [], "safe": True},
        "round":            {"passthrough": [], "safe": True},
        "min":              {"passthrough": [0], "safe": False},
        "max":              {"passthrough": [0], "safe": False},
        "sum":              {"passthrough": [], "safe": True},
        "any":              {"passthrough": [], "safe": True},
        "all":              {"passthrough": [], "safe": True},
        "range":            {"passthrough": [], "safe": True},
        "print":            {"passthrough": [], "safe": True},

        # ===== 编解码（透传但不安全） =====
        "base64.b64encode":     {"passthrough": [0], "safe": False},
        "base64.b64decode":     {"passthrough": [0], "safe": False},
        "base64.urlsafe_b64encode": {"passthrough": [0], "safe": False},
        "base64.urlsafe_b64decode": {"passthrough": [0], "safe": False},
        "json.dumps":           {"passthrough": [0], "safe": False},
        "json.loads":           {"passthrough": [0], "safe": False},
        "pickle.dumps":         {"passthrough": [0], "safe": False},
        "pickle.loads":         {"passthrough": [0], "safe": False},  # 不安全但透传
        "urllib.parse.quote":   {"passthrough": [0], "safe": False},
        "urllib.parse.unquote": {"passthrough": [0], "safe": False},
        "urllib.parse.urlencode": {"passthrough": [0], "safe": False},
        "urllib.parse.urlparse":  {"passthrough": [0], "safe": False},
        "yaml.dump":            {"passthrough": [0], "safe": False},
        "yaml.load":            {"passthrough": [0], "safe": False},

        # ===== 安全过滤函数 =====
        "html.escape":              {"passthrough": [0], "safe": True},
        "markupsafe.escape":        {"passthrough": [0], "safe": True},
        "markupsafe.Markup":        {"passthrough": [0], "safe": True},
        "bleach.clean":             {"passthrough": [0], "safe": True},
        "bleach.linkify":           {"passthrough": [0], "safe": True},
        "cgi.escape":               {"passthrough": [0], "safe": True},
        "xml.sax.saxutils.escape":  {"passthrough": [0], "safe": True},
        "re.escape":                {"passthrough": [0], "safe": True},
        "shlex.quote":              {"passthrough": [0], "safe": True},
        "werkzeug.utils.escape":    {"passthrough": [0], "safe": True},
        "django.utils.html.escape": {"passthrough": [0], "safe": True},
        "django.utils.http.urlquote": {"passthrough": [0], "safe": True},

        # ===== 文件/IO（透传路径参数） =====
        "os.path.join":         {"passthrough": [0, 1], "safe": False},
        "os.path.normpath":     {"passthrough": [0], "safe": False},
        "os.path.abspath":      {"passthrough": [0], "safe": False},
        "os.path.realpath":     {"passthrough": [0], "safe": False},
        "os.path.basename":     {"passthrough": [0], "safe": False},
        "os.path.dirname":      {"passthrough": [0], "safe": False},
        "os.path.expanduser":   {"passthrough": [0], "safe": False},

        # ===== 正则匹配 =====
        "re.sub":       {"passthrough": [2], "safe": False},  # 透传 subject(第3个参数)
        "re.match":     {"passthrough": [1], "safe": False},
        "re.search":    {"passthrough": [1], "safe": False},
        "re.findall":   {"passthrough": [1], "safe": False},
        "re.split":     {"passthrough": [1], "safe": False},

        # ===== Django =====
        "django.utils.safestring.mark_safe":  {"passthrough": [0], "safe": False},  # 标记安全但不实际过滤
        "django.utils.safestring.SafeString": {"passthrough": [0], "safe": False},
        "django.template.loader.render_to_string": {"passthrough": [0], "safe": False},

        # ===== Flask =====
        "flask.escape":            {"passthrough": [0], "safe": True},  # 同 markupsafe.escape
        "flask.render_template":   {"passthrough": [0], "safe": False},
        "flask.render_template_string": {"passthrough": [0], "safe": False},
        "flask.redirect":          {"passthrough": [0], "safe": False},
        "flask.url_for":           {"passthrough": [], "safe": True},
        "flask.jsonify":           {"passthrough": [0], "safe": False},
        "flask.send_file":         {"passthrough": [0], "safe": False},

        # ===== FastAPI/Starlette =====
        "fastapi.Query":    {"passthrough": [0], "safe": False},
        "fastapi.Path":     {"passthrough": [0], "safe": False},
        "fastapi.Body":     {"passthrough": [0], "safe": False},
        "fastapi.Form":     {"passthrough": [0], "safe": False},
        "fastapi.File":     {"passthrough": [0], "safe": False},
        "fastapi.Depends":  {"passthrough": [0], "safe": False},
        "starlette.responses.HTMLResponse": {"passthrough": [0], "safe": False},
        "starlette.responses.JSONResponse": {"passthrough": [0], "safe": False},

        # ===== Tornado =====
        "tornado.escape.xhtml_escape":  {"passthrough": [0], "safe": True},
        "tornado.escape.url_escape":    {"passthrough": [0], "safe": False},
        "tornado.escape.json_encode":   {"passthrough": [0], "safe": False},
        "tornado.escape.squeeze":       {"passthrough": [0], "safe": False},

        # ===== Jinja2 =====
        "jinja2.escape":     {"passthrough": [0], "safe": True},
        "jinja2.Markup":     {"passthrough": [0], "safe": False},  # 标记安全但不过滤

        # ===== Celery =====
        "celery.utils.serialization.unpickle": {"passthrough": [0], "safe": False},
    }

    PHP = {
        # ===== 字符串函数 =====
        "trim":             {"passthrough": [0], "safe": False},
        "ltrim":            {"passthrough": [0], "safe": False},
        "rtrim":            {"passthrough": [0], "safe": False},
        "strtoupper":       {"passthrough": [0], "safe": False},
        "strtolower":       {"passthrough": [0], "safe": False},
        "ucfirst":          {"passthrough": [0], "safe": False},
        "lcfirst":          {"passthrough": [0], "safe": False},
        "ucwords":          {"passthrough": [0], "safe": False},
        "substr":           {"passthrough": [0], "safe": False},
        "substring":        {"passthrough": [0], "safe": False},
        "str_replace":      {"passthrough": [2], "safe": False},  # 透传 subject
        "str_ireplace":     {"passthrough": [2], "safe": False},
        "implode":          {"passthrough": [1], "safe": False},  # 透传 array
        "explode":          {"passthrough": [1], "safe": False},  # 透传 string
        "sprintf":          {"passthrough": [1], "safe": False},
        "printf":           {"passthrough": [1], "safe": False},
        "str_pad":          {"passthrough": [0], "safe": False},
        "str_repeat":       {"passthrough": [0], "safe": False},
        "strrev":           {"passthrough": [0], "safe": False},
        "str_shuffle":      {"passthrough": [0], "safe": False},
        "nl2br":            {"passthrough": [0], "safe": False},
        "chunk_split":      {"passthrough": [0], "safe": False},
        "wordwrap":         {"passthrough": [0], "safe": False},
        "strtok":           {"passthrough": [0], "safe": False},
        "parse_str":        {"passthrough": [0], "safe": False},

        # ===== 编解码 =====
        "base64_encode":        {"passthrough": [0], "safe": False},
        "base64_decode":        {"passthrough": [0], "safe": False},
        "urldecode":            {"passthrough": [0], "safe": False},
        "urlencode":            {"passthrough": [0], "safe": False},
        "rawurldecode":         {"passthrough": [0], "safe": False},
        "rawurlencode":         {"passthrough": [0], "safe": False},
        "html_entity_decode":   {"passthrough": [0], "safe": False},
        "json_encode":          {"passthrough": [0], "safe": False},
        "json_decode":          {"passthrough": [0], "safe": False},
        "serialize":            {"passthrough": [0], "safe": False},
        "unserialize":          {"passthrough": [0], "safe": False},
        "utf8_encode":          {"passthrough": [0], "safe": False},
        "utf8_decode":          {"passthrough": [0], "safe": False},
        "iconv":                {"passthrough": [2], "safe": False},  # 透传 string
        "mb_convert_encoding":  {"passthrough": [0], "safe": False},
        "mb_strtolower":        {"passthrough": [0], "safe": False},
        "mb_strtoupper":        {"passthrough": [0], "safe": False},
        "mb_substr":            {"passthrough": [0], "safe": False},
        "mb_ereg_replace":      {"passthrough": [2], "safe": False},
        "preg_replace":         {"passthrough": [2], "safe": False},  # 透传 subject

        # ===== 类型转换 =====
        "strval":       {"passthrough": [0], "safe": False},
        "intval":       {"passthrough": [], "safe": True},   # 返回整数
        "floatval":     {"passthrough": [], "safe": True},
        "settype":      {"passthrough": [], "safe": True},
        "array_values": {"passthrough": [0], "safe": False},
        "array_keys":   {"passthrough": [0], "safe": False},
        "array_map":    {"passthrough": [1], "safe": False},
        "array_filter": {"passthrough": [0], "safe": False},
        "array_merge":  {"passthrough": [0, 1], "safe": False},
        "array_reverse": {"passthrough": [0], "safe": False},
        "array_slice":  {"passthrough": [0], "safe": False},
        "array_unique": {"passthrough": [0], "safe": False},
        "sort":         {"passthrough": [0], "safe": False},
        "asort":        {"passthrough": [0], "safe": False},
        "ksort":        {"passthrough": [0], "safe": False},
        "compact":      {"passthrough": [0], "safe": False},
        "extract":      {"passthrough": [0], "safe": False},

        # ===== 安全过滤函数 =====
        "htmlspecialchars":             {"passthrough": [0], "safe": True},
        "htmlentities":                 {"passthrough": [0], "safe": True},
        "strip_tags":                   {"passthrough": [0], "safe": True},
        "mysql_real_escape_string":     {"passthrough": [0], "safe": True},
        "mysqli_real_escape_string":    {"passthrough": [0], "safe": True},
        "pg_escape_string":             {"passthrough": [0], "safe": True},
        "sqlite_escape_string":         {"passthrough": [0], "safe": True},
        "addslashes":                   {"passthrough": [0], "safe": True},
        "stripslashes":                 {"passthrough": [0], "safe": False},
        "escapeshellcmd":               {"passthrough": [0], "safe": True},
        "escapeshellarg":               {"passthrough": [0], "safe": True},
        "filter_var":                   {"passthrough": [0], "safe": True},
        "filter_input":                 {"passthrough": [], "safe": True},
        "ctype_digit":                  {"passthrough": [], "safe": True},
        "ctype_alpha":                  {"passthrough": [], "safe": True},
        "ctype_alnum":                  {"passthrough": [], "safe": True},
        "preg_match":                   {"passthrough": [], "safe": True},
        "number_format":                {"passthrough": [], "safe": True},
        "chr":                          {"passthrough": [], "safe": True},

        # ===== 不透传 =====
        "strlen":       {"passthrough": [], "safe": True},
        "strpos":       {"passthrough": [], "safe": True},
        "strrpos":      {"passthrough": [], "safe": True},
        "stripos":      {"passthrough": [], "safe": True},
        "strripos":     {"passthrough": [], "safe": True},
        "strcmp":       {"passthrough": [], "safe": True},
        "strcasecmp":   {"passthrough": [], "safe": True},
        "substr_count": {"passthrough": [], "safe": True},
        "count":        {"passthrough": [], "safe": True},
        "sizeof":       {"passthrough": [], "safe": True},
        "is_array":     {"passthrough": [], "safe": True},
        "is_string":    {"passthrough": [], "safe": True},
        "is_int":       {"passthrough": [], "safe": True},
        "is_integer":   {"passthrough": [], "safe": True},
        "is_numeric":   {"passthrough": [], "safe": True},
        "is_null":      {"passthrough": [], "safe": True},
        "is_bool":      {"passthrough": [], "safe": True},
        "isset":        {"passthrough": [], "safe": True},
        "empty":        {"passthrough": [], "safe": True},
        "defined":      {"passthrough": [], "safe": True},
        "function_exists": {"passthrough": [], "safe": True},
        "class_exists": {"passthrough": [], "safe": True},
        "method_exists": {"passthrough": [], "safe": True},
        "property_exists": {"passthrough": [], "safe": True},
        "in_array":     {"passthrough": [], "safe": True},
        "array_key_exists": {"passthrough": [], "safe": True},
        "array_search": {"passthrough": [], "safe": True},
        "print":        {"passthrough": [], "safe": True},
        "echo":         {"passthrough": [], "safe": True},
        "var_dump":     {"passthrough": [], "safe": True},
        "print_r":      {"passthrough": [], "safe": True},
        "die":          {"passthrough": [], "safe": True},
        "exit":         {"passthrough": [], "safe": True},
        "header":       {"passthrough": [], "safe": True},
        "http_response_code": {"passthrough": [], "safe": True},

        # ===== Laravel =====
        "e":                    {"passthrough": [0], "safe": True},
        "csrf_field":           {"passthrough": [], "safe": True},
        "csrf_token":           {"passthrough": [], "safe": True},
        "redirect":             {"passthrough": [0], "safe": False},
        "route":                {"passthrough": [], "safe": True},
        "asset":                {"passthrough": [], "safe": True},
        "url":                  {"passthrough": [0], "safe": False},
        "action":               {"passthrough": [], "safe": True},
        "response":             {"passthrough": [0], "safe": False},
        "old":                  {"passthrough": [0], "safe": False},
        "session":              {"passthrough": [0], "safe": False},
        "cookie":               {"passthrough": [0], "safe": False},
        "config":               {"passthrough": [0], "safe": False},
        "env":                  {"passthrough": [0], "safe": False},
        "app":                  {"passthrough": [0], "safe": False},
        "request":              {"passthrough": [0], "safe": False},
        "Illuminate\\Support\\Str::limit":     {"passthrough": [0], "safe": False},
        "Illuminate\\Support\\Str::words":     {"passthrough": [0], "safe": False},
        "Illuminate\\Support\\Str::slug":      {"passthrough": [0], "safe": False},
        "Illuminate\\Support\\Str::studly":    {"passthrough": [0], "safe": False},
        "Illuminate\\Support\\Str::camel":     {"passthrough": [0], "safe": False},
        "Illuminate\\Support\\Str::kebab":     {"passthrough": [0], "safe": False},
        "Illuminate\\Support\\Str::snake":     {"passthrough": [0], "safe": False},
        "Illuminate\\Support\\Str::title":     {"passthrough": [0], "safe": False},

        # ===== ThinkPHP =====
        "input":                {"passthrough": [0], "safe": False},
        "I":                    {"passthrough": [0], "safe": False},

        # ===== WordPress =====
        "esc_html":             {"passthrough": [0], "safe": True},
        "esc_attr":             {"passthrough": [0], "safe": True},
        "esc_url":              {"passthrough": [0], "safe": True},
        "esc_js":               {"passthrough": [0], "safe": True},
        "esc_textarea":         {"passthrough": [0], "safe": True},
        "wp_kses":              {"passthrough": [0], "safe": True},
        "wp_kses_post":         {"passthrough": [0], "safe": True},
        "sanitize_text_field":  {"passthrough": [0], "safe": True},
        "sanitize_email":       {"passthrough": [0], "safe": True},
        "sanitize_title":       {"passthrough": [0], "safe": True},
        "sanitize_file_name":   {"passthrough": [0], "safe": True},
        "wp_nonce_field":       {"passthrough": [], "safe": True},
        "wp_nonce_url":         {"passthrough": [0], "safe": False},
        "wp_verify_nonce":      {"passthrough": [], "safe": True},
        "wp_safe_redirect":     {"passthrough": [0], "safe": True},
        "absint":               {"passthrough": [], "safe": True},
        "wp_kses_allowed_html": {"passthrough": [0], "safe": True},

        # ===== CodeIgniter =====
        "xss_clean":            {"passthrough": [0], "safe": True},
        "html_escape":          {"passthrough": [0], "safe": True},
    }

    JAVASCRIPT = {
        # ===== String 方法（透传 this） =====
        "toUpperCase":      {"passthrough": [0], "safe": False},
        "toLowerCase":      {"passthrough": [0], "safe": False},
        "trim":             {"passthrough": [0], "safe": False},
        "trimStart":        {"passthrough": [0], "safe": False},
        "trimEnd":          {"passthrough": [0], "safe": False},
        "trimLeft":         {"passthrough": [0], "safe": False},
        "trimRight":        {"passthrough": [0], "safe": False},
        "replace":          {"passthrough": [0], "safe": False},
        "replaceAll":       {"passthrough": [0], "safe": False},
        "split":            {"passthrough": [0], "safe": False},
        "substring":        {"passthrough": [0], "safe": False},
        "substr":           {"passthrough": [0], "safe": False},
        "slice":            {"passthrough": [0], "safe": False},
        "concat":           {"passthrough": [0], "safe": False},
        "padStart":         {"passthrough": [0], "safe": False},
        "padEnd":           {"passthrough": [0], "safe": False},
        "repeat":           {"passthrough": [0], "safe": False},
        "toString":         {"passthrough": [0], "safe": False},
        "valueOf":          {"passthrough": [0], "safe": False},
        "charAt":           {"passthrough": [0], "safe": False},
        "charCodeAt":       {"passthrough": [], "safe": True},
        "codePointAt":      {"passthrough": [], "safe": True},
        "normalize":        {"passthrough": [0], "safe": False},
        "localeCompare":    {"passthrough": [], "safe": True},
        "match":            {"passthrough": [0], "safe": False},
        "matchAll":         {"passthrough": [0], "safe": False},
        "search":           {"passthrough": [], "safe": True},
        "at":               {"passthrough": [0], "safe": False},
        "fontsize":         {"passthrough": [0], "safe": False},
        "fixed":            {"passthrough": [0], "safe": False},
        "bold":             {"passthrough": [0], "safe": False},
        "italics":          {"passthrough": [0], "safe": False},
        "link":             {"passthrough": [0], "safe": False},

        # ===== Array 方法 =====
        "map":              {"passthrough": [0], "safe": False},
        "filter":           {"passthrough": [0], "safe": False},
        "reduce":           {"passthrough": [0], "safe": False},
        "flat":             {"passthrough": [0], "safe": False},
        "flatMap":          {"passthrough": [0], "safe": False},
        "sort":             {"passthrough": [0], "safe": False},
        "reverse":          {"passthrough": [0], "safe": False},
        "splice":           {"passthrough": [0], "safe": False},
        "slice":            {"passthrough": [0], "safe": False},
        "concat":           {"passthrough": [0], "safe": False},
        "join":             {"passthrough": [0], "safe": False},
        "find":             {"passthrough": [0], "safe": False},
        "findIndex":        {"passthrough": [], "safe": True},
        "indexOf":          {"passthrough": [], "safe": True},
        "lastIndexOf":      {"passthrough": [], "safe": True},
        "includes":         {"passthrough": [], "safe": True},
        "every":            {"passthrough": [], "safe": True},
        "some":             {"passthrough": [], "safe": True},
        "forEach":          {"passthrough": [], "safe": True},
        "push":             {"passthrough": [], "safe": True},
        "pop":              {"passthrough": [0], "safe": False},
        "shift":            {"passthrough": [0], "safe": False},
        "unshift":          {"passthrough": [], "safe": True},
        "fill":             {"passthrough": [0], "safe": False},
        "copyWithin":       {"passthrough": [0], "safe": False},

        # ===== 全局函数 =====
        "String":           {"passthrough": [0], "safe": False},
        "Number":           {"passthrough": [], "safe": True},
        "Boolean":          {"passthrough": [], "safe": True},
        "parseInt":         {"passthrough": [], "safe": True},
        "parseFloat":       {"passthrough": [], "safe": True},
        "isNaN":            {"passthrough": [], "safe": True},
        "isFinite":         {"passthrough": [], "safe": True},
        "Array.from":       {"passthrough": [0], "safe": False},
        "Array.of":         {"passthrough": [0], "safe": False},
        "Object.keys":      {"passthrough": [0], "safe": False},
        "Object.values":    {"passthrough": [0], "safe": False},
        "Object.entries":   {"passthrough": [0], "safe": False},
        "Object.assign":    {"passthrough": [0, 1], "safe": False},
        "Object.create":    {"passthrough": [0], "safe": False},

        # ===== 编解码 =====
        "JSON.stringify":       {"passthrough": [0], "safe": False},
        "JSON.parse":           {"passthrough": [0], "safe": False},
        "encodeURI":            {"passthrough": [0], "safe": False},
        "encodeURIComponent":   {"passthrough": [0], "safe": False},
        "decodeURI":            {"passthrough": [0], "safe": False},
        "decodeURIComponent":   {"passthrough": [0], "safe": False},
        "btoa":                 {"passthrough": [0], "safe": False},
        "atob":                 {"passthrough": [0], "safe": False},
        "escape":               {"passthrough": [0], "safe": False},
        "unescape":             {"passthrough": [0], "safe": False},

        # ===== 安全过滤 =====
        "DOMPurify.sanitize":   {"passthrough": [0], "safe": True},
        "sanitize":             {"passthrough": [0], "safe": True},

        # ===== 不透传 =====
        "length":       {"passthrough": [], "safe": True},
        "typeof":       {"passthrough": [], "safe": True},
        "instanceof":   {"passthrough": [], "safe": True},
        "console.log":  {"passthrough": [], "safe": True},
        "console.warn": {"passthrough": [], "safe": True},
        "console.error": {"passthrough": [], "safe": True},
        "alert":        {"passthrough": [], "safe": True},
        "Math.floor":   {"passthrough": [], "safe": True},
        "Math.ceil":    {"passthrough": [], "safe": True},
        "Math.round":   {"passthrough": [], "safe": True},
        "Math.abs":     {"passthrough": [], "safe": True},
        "Math.max":     {"passthrough": [], "safe": True},
        "Math.min":     {"passthrough": [], "safe": True},
        "Math.random":  {"passthrough": [], "safe": True},

        # ===== Express =====
        "express":              {"passthrough": [], "safe": True},

        # ===== jQuery =====
        "html":                 {"passthrough": [0], "safe": False},
        "append":               {"passthrough": [0], "safe": False},
        "prepend":              {"passthrough": [0], "safe": False},
        "after":                {"passthrough": [0], "safe": False},
        "before":               {"passthrough": [0], "safe": False},
        "replaceWith":          {"passthrough": [0], "safe": False},
        "text":                 {"passthrough": [], "safe": True},
        "attr":                 {"passthrough": [1], "safe": False},
        "val":                  {"passthrough": [0], "safe": False},
        "css":                  {"passthrough": [1], "safe": False},

        # ===== Vue.js =====
        "v-html":               {"passthrough": [0], "safe": False},
        "$createElement":        {"passthrough": [0], "safe": False},

        # ===== React =====
        "dangerouslySetInnerHTML": {"passthrough": [0], "safe": False},

        # ===== template engines =====
        "res.render":           {"passthrough": [0], "safe": False},
        "res.send":             {"passthrough": [0], "safe": False},
        "res.json":             {"passthrough": [0], "safe": False},
        "res.sendFile":         {"passthrough": [0], "safe": False},
        "res.redirect":         {"passthrough": [0], "safe": False},
        "res.write":            {"passthrough": [0], "safe": False},
        "ejs.render":           {"passthrough": [0], "safe": False},
        "ejs.renderFile":       {"passthrough": [0], "safe": False},
        "pug.render":           {"passthrough": [0], "safe": False},
        "handlebars.compile":   {"passthrough": [0], "safe": False},
        "nunjucks.render":      {"passthrough": [0], "safe": False},
    }

    JAVA = {
        # ===== String 方法（透传 this） =====
        "toUpperCase":      {"passthrough": [0], "safe": False},
        "toLowerCase":      {"passthrough": [0], "safe": False},
        "trim":             {"passthrough": [0], "safe": False},
        "strip":            {"passthrough": [0], "safe": False},
        "stripLeading":     {"passthrough": [0], "safe": False},
        "stripTrailing":    {"passthrough": [0], "safe": False},
        "replace":          {"passthrough": [0], "safe": False},
        "replaceAll":       {"passthrough": [0], "safe": False},
        "replaceFirst":     {"passthrough": [0], "safe": False},
        "substring":        {"passthrough": [0], "safe": False},
        "split":            {"passthrough": [0], "safe": False},
        "concat":           {"passthrough": [0], "safe": False},
        "toString":         {"passthrough": [0], "safe": False},
        "valueOf":          {"passthrough": [0], "safe": False},
        "format":           {"passthrough": [1], "safe": False},
        "getBytes":         {"passthrough": [0], "safe": False},
        "toCharArray":      {"passthrough": [0], "safe": False},
        "intern":           {"passthrough": [0], "safe": False},
        "indent":           {"passthrough": [0], "safe": False},
        "stripIndent":      {"passthrough": [0], "safe": False},
        "translateEscapes": {"passthrough": [0], "safe": False},
        "formatted":        {"passthrough": [0], "safe": False},
        "join":             {"passthrough": [1], "safe": False},
        "repeat":           {"passthrough": [0], "safe": False},
        "copyValueOf":      {"passthrough": [0], "safe": False},
        "contentEquals":    {"passthrough": [], "safe": True},
        "subSequence":      {"passthrough": [0], "safe": False},

        # ===== StringBuilder/StringBuffer =====
        "append":           {"passthrough": [0], "safe": False},
        "insert":           {"passthrough": [0], "safe": False},
        "delete":           {"passthrough": [0], "safe": False},
        "reverse":          {"passthrough": [0], "safe": False},

        # ===== 安全过滤 =====
        "StringEscapeUtils.escapeHtml4":        {"passthrough": [0], "safe": True},
        "StringEscapeUtils.escapeHtml3":        {"passthrough": [0], "safe": True},
        "StringEscapeUtils.escapeXml":          {"passthrough": [0], "safe": True},
        "StringEscapeUtils.escapeJava":         {"passthrough": [0], "safe": True},
        "StringEscapeUtils.escapeEcmaScript":   {"passthrough": [0], "safe": True},
        "StringEscapeUtils.escapeSql":          {"passthrough": [0], "safe": True},
        "StringEscapeUtils.escapeXml10":        {"passthrough": [0], "safe": True},
        "StringEscapeUtils.escapeXml11":        {"passthrough": [0], "safe": True},
        "ESAPI.encoder.encodeForHTML":          {"passthrough": [0], "safe": True},
        "ESAPI.encoder.encodeForJavaScript":    {"passthrough": [0], "safe": True},
        "ESAPI.encoder.encodeForSQL":           {"passthrough": [0], "safe": True},
        "Encode.forHtml":                       {"passthrough": [0], "safe": True},
        "Encode.forHtmlContent":                {"passthrough": [0], "safe": True},
        "Encode.forJavaScript":                 {"passthrough": [0], "safe": True},
        "Encode.forUriComponent":               {"passthrough": [0], "safe": True},

        # ===== 不透传 =====
        "length":       {"passthrough": [], "safe": True},
        "isEmpty":      {"passthrough": [], "safe": True},
        "isBlank":      {"passthrough": [], "safe": True},
        "equals":       {"passthrough": [], "safe": True},
        "equalsIgnoreCase": {"passthrough": [], "safe": True},
        "compareTo":    {"passthrough": [], "safe": True},
        "compareToIgnoreCase": {"passthrough": [], "safe": True},
        "hashCode":     {"passthrough": [], "safe": True},
        "contains":     {"passthrough": [], "safe": True},
        "indexOf":      {"passthrough": [], "safe": True},
        "lastIndexOf":  {"passthrough": [], "safe": True},
        "startsWith":   {"passthrough": [], "safe": True},
        "endsWith":     {"passthrough": [], "safe": True},
        "matches":      {"passthrough": [], "safe": True},
        "getClass":     {"passthrough": [], "safe": True},
        "charAt":       {"passthrough": [0], "safe": False},
        "codePointAt":  {"passthrough": [], "safe": True},
        "hashCode":     {"passthrough": [], "safe": True},

        # ===== Spring Framework =====
        "HtmlUtils.htmlEscape":              {"passthrough": [0], "safe": True},
        "HtmlUtils.htmlEscapeDecimal":       {"passthrough": [0], "safe": True},
        "HtmlUtils.htmlEscapeHex":           {"passthrough": [0], "safe": True},
        "JavascriptUtils.javaScriptEscape":  {"passthrough": [0], "safe": True},

        # ===== Servlet =====
        "getParameter":         {"passthrough": [0], "safe": False},
        "getParameterValues":   {"passthrough": [0], "safe": False},
        "getParameterMap":      {"passthrough": [0], "safe": False},
        "getHeader":            {"passthrough": [0], "safe": False},
        "getHeaders":           {"passthrough": [0], "safe": False},
        "getHeaderNames":       {"passthrough": [0], "safe": False},
        "getCookies":           {"passthrough": [0], "safe": False},
        "getQueryString":       {"passthrough": [0], "safe": False},
        "getRequestURI":        {"passthrough": [0], "safe": False},
        "getContextPath":       {"passthrough": [0], "safe": False},
        "getPathInfo":          {"passthrough": [0], "safe": False},
        "getInputStream":       {"passthrough": [0], "safe": False},
        "getReader":            {"passthrough": [0], "safe": False},
        "getAttribute":         {"passthrough": [0], "safe": False},
        "getSession":           {"passthrough": [0], "safe": False},
        "getServletContext":    {"passthrough": [0], "safe": False},

        # ===== Response sinks =====
        "getWriter":            {"passthrough": [0], "safe": False},
        "getOutputStream":      {"passthrough": [0], "safe": False},
        "setHeader":            {"passthrough": [1], "safe": False},
        "addHeader":            {"passthrough": [1], "safe": False},
        "sendRedirect":         {"passthrough": [0], "safe": False},
        "sendError":            {"passthrough": [0], "safe": False},
        "addCookie":            {"passthrough": [0], "safe": False},

        # ===== MyBatis =====
        # ${} interpolation is unsafe, handled at rule level

        # ===== Jackson/Gson =====
        "readValue":            {"passthrough": [0], "safe": False},
        "readTree":             {"passthrough": [0], "safe": False},
        "writeValueAsString":   {"passthrough": [0], "safe": False},
        "toJson":               {"passthrough": [0], "safe": False},
        "fromJson":             {"passthrough": [0], "safe": False},
    }

    @classmethod
    def lookup(cls, language, func_name):
        """
        查询内置函数知识库

        :param language: "python", "php", "javascript", "java"
        :param func_name: 函数/方法名
        :return: {"passthrough": [...], "safe": bool} or None
        """
        knowledge_map = {
            "python": cls.PYTHON,
            "php": cls.PHP,
            "javascript": cls.JAVASCRIPT,
            "java": cls.JAVA,
        }

        kb = knowledge_map.get(language)
        if not kb:
            return None

        # 精确匹配
        if func_name in kb:
            return kb[func_name]

        # 尝试短名匹配（方法名不带类/模块前缀）
        # 如 "html.escape" → 尝试 "escape"
        if "." in func_name:
            short_name = func_name.split(".")[-1]
            if short_name in kb:
                return kb[short_name]

        return None
