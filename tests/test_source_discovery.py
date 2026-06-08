"""Source Discovery benchmark tests — 用户自定义 source producer 发现能力验证。

测试场景：
1. PHP: getInput() 内部访问 $_GET，被 Source Discovery 标记为 source producer
2. PHP: safeHelper() 返回硬编码值，不应被标记为 source producer
3. JS: getUserInput() 内部访问 req.query，被标记为 source producer
4. JS: safeHelper() 返回硬编码值，不应被标记
5. Go: getUserInput() 内部访问 r.URL.Query()，被标记为 source producer
6. C: read_user_input() 内部调用 fgets(stdin)，被标记为 source producer
7. C: get_safe_value() 返回硬编码值，不应被标记
8. C: read_env_config() 调用 getenv，被标记为 source producer
"""
import os
import sys
import pytest

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Kunlun_M.settings')
import django
django.setup()

from Kunlun_M.settings import PROJECT_DIRECTORY

# PHP
from core.core_engine.php.parser import scan_parser as php_scan_parser
from core.pretreatment import ast_object as _ast_obj

# JS
from core.core_engine.javascript.parser import scan_parser as js_scan_parser

# Go
from core.core_engine.go.parser import scan_parser as go_scan_parser

# C
from core.core_engine.c.parser import scan_parser as c_scan_parser


# ===========================================================================
# Helper: 初始化预处理
# ===========================================================================

def _init_php_ast():
    """初始化 PHP AST 预处理（source_discovery 模块需要）"""
    runtime_files = [('.php', {'list': [
        "v_source_discovery_producer.php",
        "v_source_discovery_discrimination.php",
    ]})]
    _ast_obj.init_pre(
        PROJECT_DIRECTORY + '/tests/vulnerabilities/',
        runtime_files
    )
    _ast_obj.pre_ast_all(['php'])


def _init_js_ast():
    """初始化 JS AST 预处理"""
    runtime_files = [('.js', {'list': [
        "11_source_discovery_producer.js",
        "12_source_discovery_discrimination.js",
    ]})]
    _ast_obj.init_pre(
        PROJECT_DIRECTORY + '/tests/nodejs/',
        runtime_files
    )
    _ast_obj.pre_ast_all(['javascript'])


# ===========================================================================
# PHP Tests
# ===========================================================================

class TestPHPSourceDiscovery:
    """PHP Source Discovery: 用户自定义 source producer"""

    def test_producer_detected(self):
        """getInput() 内部访问 $_GET，echo $safeInput 应被检出"""
        _init_php_ast()
        fpath = PROJECT_DIRECTORY + '/tests/vulnerabilities/v_source_discovery_producer.php'
        # line 24: echo $safeInput — $safeInput 来自 getInput("cmd") -> $_GET
        result = php_scan_parser(['echo'], 24, fpath)
        assert result, "echo $safeInput 应检出 (getInput -> $_GET)"

    def test_discrimination_safe_not_detected(self):
        """safeHelper() 返回硬编码值，echo $safe 不应被检出为可控漏洞 (code != 1)"""
        _init_php_ast()
        fpath = PROJECT_DIRECTORY + '/tests/vulnerabilities/v_source_discovery_discrimination.php'
        # line 23: echo $safe — $safe 来自 safeHelper() 硬编码值
        result = php_scan_parser(['echo'], 23, fpath)
        # 引擎可能返回 code 3 (NewFind/未确认) 或空，但不应该是 code 1 (确认可控)
        if result:
            for r in result:
                assert r.get('code') != 1, "echo $safe 不应检出为可控漏洞 (safeHelper 是硬编码)"

    def test_discrimination_user_detected(self):
        """getUserData() 访问 $_POST，echo $user 应检出"""
        _init_php_ast()
        fpath = PROJECT_DIRECTORY + '/tests/vulnerabilities/v_source_discovery_discrimination.php'
        # line 24: echo $user — $user 来自 getUserData("name") -> $_POST
        result = php_scan_parser(['echo'], 24, fpath)
        assert result, "echo $user 应检出 (getUserData -> $_POST)"


# ===========================================================================
# JavaScript Tests
# ===========================================================================

class TestJSSourceDiscovery:
    """JavaScript Source Discovery: 用户自定义 source producer"""

    def test_producer_detected(self):
        """getUserInput() 内部访问 req.query，eval(cmd) 应检出"""
        _init_js_ast()
        fpath = PROJECT_DIRECTORY + '/tests/nodejs/11_source_discovery_producer.js'
        # line 23: eval(cmd) — cmd 来自 handleRequest -> getUserInput -> req.query
        result = js_scan_parser(['eval'], 23, fpath)
        assert result, "eval(cmd) 应检出 (getUserInput -> req.query)"

    def test_discrimination_safe_not_detected(self):
        """safeHelper() 返回硬编码值，console.log(safe) 不应被检出为可控漏洞 (code != 1)"""
        _init_js_ast()
        fpath = PROJECT_DIRECTORY + '/tests/nodejs/12_source_discovery_discrimination.js'
        # line 22: console.log(safe) — safe 来自 safeHelper() 硬编码值
        result = js_scan_parser(['console.log'], 22, fpath)
        if result:
            for r in result:
                assert r.get('code') != 1, "console.log(safe) 不应检出为可控漏洞 (safeHelper 是硬编码)"

    def test_discrimination_user_detected(self):
        """getUserData() 访问 req.body，document.write(user) 应检出"""
        _init_js_ast()
        fpath = PROJECT_DIRECTORY + '/tests/nodejs/12_source_discovery_discrimination.js'
        # line 23: document.write(user) — user 来自 getUserData -> req.body
        result = js_scan_parser(['document.write'], 23, fpath)
        assert result, "document.write(user) 应检出 (getUserData -> req.body)"


# ===========================================================================
# Go Tests
# ===========================================================================

class TestGoSourceDiscovery:
    """Go Source Discovery: 用户自定义 source producer"""

    def test_producer_detected(self):
        """getUserInput() 内部访问 r.URL.Query()，exec.Command 应检出"""
        fpath = PROJECT_DIRECTORY + '/tests/vulnerabilities/go/test_source_discovery_producer.go'
        # line 22: exec.Command("sh", "-c", cmd).Run() — cmd 来自 getUserInput -> r.URL.Query()
        result = go_scan_parser(['exec.Command'], 22, fpath)
        assert result, "exec.Command 应检出 (getUserInput -> r.URL.Query)"
        # 验证结果格式
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0].get('code') == 1


# ===========================================================================
# C Tests
# ===========================================================================

class TestCSourceDiscovery:
    """C/C++ Source Discovery: 用户自定义 source producer"""

    def test_producer_detected(self):
        """read_user_input() 内部调用 fgets(stdin)，system() 应检出"""
        fpath = PROJECT_DIRECTORY + '/tests/c/23_source_discovery_producer.c'
        # line 22: system(read_user_input()) — read_user_input -> fgets(stdin)
        result = c_scan_parser(['system'], 22, fpath)
        assert result, "system(process_data()) 应检出 (read_user_input -> fgets)"
        assert isinstance(result, list)
        assert len(result) > 0
        assert result[0].get('code') == 1

    def test_discrimination_safe_not_detected(self):
        """get_safe_value() 返回硬编码值，printf(safe) 不应被检出为可控漏洞 (code != 1)"""
        fpath = PROJECT_DIRECTORY + '/tests/c/24_source_discovery_discrimination.c'
        # line 27: printf(safe) — safe 来自 get_safe_value() 硬编码
        result = c_scan_parser(['printf'], 27, fpath)
        if result:
            for r in result:
                assert r.get('code') != 1, "printf(safe) 不应检出为可控漏洞 (get_safe_value 是硬编码)"

    def test_discrimination_env_detected(self):
        """read_env_config() 调用 getenv，printf(config) 应检出"""
        fpath = PROJECT_DIRECTORY + '/tests/c/24_source_discovery_discrimination.c'
        # line 28: printf(config) — config 来自 read_env_config("PATH") -> getenv
        result = c_scan_parser(['printf'], 28, fpath)
        assert result, "printf(config) 应检出 (read_env_config -> getenv)"
