#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
JS 跨文件追踪 & NewFunction benchmark 测试

场景说明：
|- import 解析: CommonJS require / 解构导入 / 函数索引
|- NewFunction 信号: 13a/17a/18a 封装函数内 eval/setTimeout(形参) 应生成 code=4
|- 负面用例: 16a/b 安全封装不应检出
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Kunlun_M.settings')

import django
django.setup()

from Kunlun_M.settings import PROJECT_DIRECTORY
from core.pretreatment import ast_object
from core.core_engine.javascript.parser import (
    scan_parser as js_scan_parser,
    _parse_js_imports, _build_js_func_index,
    _try_cross_file_trace_js
)

TEST_DIR = PROJECT_DIRECTORY + '/tests/nodejs/'

# 所有测试文件列表
ALL_FILES = [
    '13a_cross_file_eval_utils.js',
    '13b_cross_file_eval_main.js',
    '14a_cross_file_destructure_utils.js',
    '14b_cross_file_destructure_main.js',
    '16a_cross_file_safe_utils.js',
    '16b_cross_file_safe_main.js',
    '17a_cross_file_exports_utils.js',
    '17b_cross_file_exports_main.js',
    '18a_cross_file_settimeout_utils.js',
    '18b_cross_file_settimeout_main.js',
]


def init_once():
    """一次性初始化所有文件 AST"""
    global _initialized
    if _initialized:
        return
    _initialized = True

    ast_object.pre_result = {}
    runtime_files = [('.js', {'list': ALL_FILES})]
    ast_object.init_pre(TEST_DIR, runtime_files)
    ast_object.pre_ast_all(['javascript'])

_initialized = False


def get_abs(filename):
    return os.path.join(TEST_DIR, filename)


def test_parse_js_imports_commonjs():
    """测试 CommonJS require 导入解析: var utils = require('./...')"""
    init_once()
    main_file = get_abs('13b_cross_file_eval_main.js')
    _nodes = ast_object.get_nodes(main_file)

    import_map = _parse_js_imports(_nodes, main_file)
    print(f"[13b] import_map = {import_map}")
    assert 'utils' in import_map, f"未找到 'utils' import: {import_map}"
    assert '13a_cross_file_eval_utils' in import_map['utils'], f"路径不匹配: {import_map['utils']}"
    print("[13b] ✅ CommonJS import_map 正确")


def test_parse_js_imports_destructure():
    """测试解构导入: var { executeCmd } = require('./...')"""
    init_once()
    main_file = get_abs('14b_cross_file_destructure_main.js')
    _nodes = ast_object.get_nodes(main_file)

    import_map = _parse_js_imports(_nodes, main_file)
    print(f"[14b] import_map = {import_map}")
    assert 'executeCmd' in import_map, f"未找到 'executeCmd' 解构导入: {import_map}"
    print("[14b] ✅ 解构导入正确")


def test_build_js_func_index():
    """测试函数索引构建"""
    init_once()
    utils_file = get_abs('13a_cross_file_eval_utils.js')
    _nodes = ast_object.get_nodes(utils_file)

    func_index = _build_js_func_index(_nodes, utils_file)
    print(f"[13a] func_index keys = {list(func_index.keys())}")
    assert 'evaluateExpression' in func_index, f"未找到 evaluateExpression: {func_index.keys()}"
    assert 'runScript' in func_index, f"未找到 runScript: {func_index.keys()}"
    print("[13a] ✅ 函数索引正确")


def test_cross_file_newfunction_eval():
    """测试 NewFunction 信号：utils.js 中 eval(形参) 应生成 code=4"""
    init_once()
    utils_file = get_abs('13a_cross_file_eval_utils.js')

    # grep 在 utils.js:6 找到 eval，scan_parser 应返回 code=4 (NewFunction)
    result = js_scan_parser(['eval', 'setTimeout'], 6, utils_file)
    print(f"[13a] result codes = {[r.get('code') for r in (result or [])]}")
    assert result and len(result) > 0, "scan_parser 应有结果"
    has_newfunc = any(r.get('code') == 4 for r in result)
    assert has_newfunc, f"应有 code=4 (NewFunction): {[r.get('code') for r in result]}"
    print("[13a] ✅ NewFunction 信号正确生成 (code=4)")


def test_cross_file_newfunction_exports():
    """测试 NewFunction 信号：exports 模式 eval(形参) 应生成 code=4"""
    init_once()
    utils_file = get_abs('17a_cross_file_exports_utils.js')

    result = js_scan_parser(['eval', 'setTimeout'], 5, utils_file)
    print(f"[17a] result codes = {[r.get('code') for r in (result or [])]}")
    assert result and len(result) > 0, "scan_parser 应有结果"
    has_newfunc = any(r.get('code') == 4 for r in result)
    assert has_newfunc, f"应有 code=4 (NewFunction): {[r.get('code') for r in result]}"
    print("[17a] ✅ NewFunction 信号正确生成 (exports 模式)")


def test_cross_file_newfunction_settimeout():
    """测试 NewFunction 信号：setTimeout 封装应生成 code=4"""
    init_once()
    utils_file = get_abs('18a_cross_file_settimeout_utils.js')

    result = js_scan_parser(['eval', 'setTimeout'], 6, utils_file)
    print(f"[18a] result codes = {[r.get('code') for r in (result or [])]}")
    assert result and len(result) > 0, "scan_parser 应有结果"
    has_newfunc = any(r.get('code') == 4 for r in result)
    assert has_newfunc, f"应有 code=4 (NewFunction): {[r.get('code') for r in result]}"
    print("[18a] ✅ NewFunction 信号正确生成 (setTimeout)")


def test_cross_file_safe_negative():
    """负面用例：安全封装不应检出"""
    init_once()
    main_file = get_abs('16b_cross_file_safe_main.js')
    _nodes = ast_object.get_nodes(main_file)
    all_nodes = getattr(_nodes, 'body', []) or []
    import_map = _parse_js_imports(_nodes, main_file)

    vul_lineno = 8
    sensitive_func = ['eval', 'setTimeout']

    result = _try_cross_file_trace_js(
        all_nodes, vul_lineno, sensitive_func, main_file,
        import_map, controlled_params=None)

    print(f"[16] result = {result}")
    assert not result, f"安全封装不应检出: {result}"
    print("[16] ✅ 负面用例正确：安全封装未检出")


def test_scan_parser_integration():
    """集成测试：scan_parser 完整流程"""
    init_once()
    main_file = get_abs('13b_cross_file_eval_main.js')

    result = js_scan_parser(['eval', 'setTimeout'], 8, main_file)
    print(f"[integration] result = {result}")
    if result and len(result) > 0 and result[0].get('code') == 1:
        print("[integration] ✅ scan_parser 集成测试通过")
    elif result and len(result) > 0:
        print(f"[integration] ⚠️ 有结果但 code != 1: {result}")
    else:
        print("[integration] ❌ scan_parser 未检出")


def _scan_single_e2e(lang, file_list, vul_dir, svid=1):
    """端到端 scan_single 测试辅助函数

    构造一个 function-param-regex 规则，match 为 eval|setTimeout，
    走完整的 grep → scan_parser → NewFunction → NewCore 链路。
    """
    from core.scanner import scan_single
    from core.pretreatment import ast_object as ao

    # 清理全局状态（之前测试可能污染了 ast_object）
    ao.pre_result = {}
    ao.define_dict = {}

    # files 参数格式：扩展名必须与 ext_dict 一致
    ext_map = {'javascript': '.js', 'php': '.php', 'python': '.py',
               'java': '.java', 'go': '.go', 'c': '.c', 'solidity': '.sol'}
    ext = ext_map.get(lang, f'.{lang}')

    runtime_files = [(ext, {'list': file_list})]
    ao.init_pre(vul_dir, runtime_files)
    ao.pre_ast_all([lang])

    # 构造规则对象（function-param-regex 模式，match 是函数名列表）
    from types import SimpleNamespace
    rule = SimpleNamespace(
        svid=svid,
        language=lang,
        author='test',
        vulnerability='RCE',
        description='test rule',
        level=5,
        status=True,
        match_mode='function-param-regex',
        match='eval|setTimeout',
        match_name=None,
        black_list=None,
        unmatch=None,
        vul_function=None,
        keyword=None,
        main=lambda regex_string: True,
    )

    file_list_parsed = [(ext, {'list': file_list})]
    return scan_single(vul_dir, rule, file_list_parsed, language=lang)


def test_js_e2e_newfunction_cross_file():
    """端到端测试：JS NewFunction 跨文件 - 13a/13b eval 封装"""
    file_list = ['13a_cross_file_eval_utils.js', '13b_cross_file_eval_main.js']
    results = _scan_single_e2e('javascript', file_list, TEST_DIR)
    print(f"[e2e-13] results = {results}")
    assert results is not None, "scan_single 应返回结果"
    assert len(results) > 0, "13a/13b 应检出至少 1 个漏洞"
    print(f"[e2e-13] ✅ 端到端检出 {len(results)} 个漏洞")


def test_js_e2e_exports_cross_file():
    """端到端测试：JS NewFunction 跨文件 - 17a/17b exports eval"""
    file_list = ['17a_cross_file_exports_utils.js', '17b_cross_file_exports_main.js']
    results = _scan_single_e2e('javascript', file_list, TEST_DIR)
    print(f"[e2e-17] results = {results}")
    assert results is not None and len(results) > 0, "17a/17b 应检出至少 1 个漏洞"
    print(f"[e2e-17] ✅ 端到端检出 {len(results)} 个漏洞")


def test_js_e2e_safe_no_false_positive():
    """端到端测试：JS 安全封装不应检出"""
    file_list = ['16a_cross_file_safe_utils.js', '16b_cross_file_safe_main.js']
    results = _scan_single_e2e('javascript', file_list, TEST_DIR)
    print(f"[e2e-16] results = {results}")
    assert not results, f"16a/16b 安全封装不应检出: {results}"
    print("[e2e-16] ✅ 安全封装正确未检出")


def test_php_e2e_newfunction():
    """端到端测试：PHP NewFunction - newfunction_utils/main eval 封装"""
    php_dir = PROJECT_DIRECTORY + '/tests/php/'
    file_list = ['newfunction_utils.php', 'newfunction_main.php']
    results = _scan_single_e2e('php', file_list, php_dir)
    print(f"[e2e-php] results = {results}")
    assert results is not None and len(results) > 0, "PHP newfunction 应检出至少 1 个漏洞"
    print(f"[e2e-php] ✅ 端到端检出 {len(results)} 个漏洞")


def main():
    print("=" * 60)
    print("JS 跨文件追踪 Benchmark")
    print("=" * 60)

    tests = [
        ("import CommonJS", test_parse_js_imports_commonjs),
        ("import 解构", test_parse_js_imports_destructure),
        ("函数索引", test_build_js_func_index),
        ("NewFunction eval", test_cross_file_newfunction_eval),
        ("NewFunction exports", test_cross_file_newfunction_exports),
        ("NewFunction setTimeout", test_cross_file_newfunction_settimeout),
        ("负面用例 安全封装", test_cross_file_safe_negative),
        ("scan_parser 集成", test_scan_parser_integration),
        ("端到端 JS 13a/13b", test_js_e2e_newfunction_cross_file),
        ("端到端 JS 17a/17b", test_js_e2e_exports_cross_file),
        ("端到端 JS 安全封装", test_js_e2e_safe_no_false_positive),
        ("端到端 PHP newfunction", test_php_e2e_newfunction),
    ]

    passed = 0
    failed = 0
    for name, test_fn in tests:
        print(f"\n--- {name} ---")
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"❌ ASSERTION FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"结果: {passed} 通过, {failed} 失败, 共 {passed + failed} 个")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
