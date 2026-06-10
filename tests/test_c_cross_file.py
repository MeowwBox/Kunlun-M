# -*- coding: utf-8 -*-
"""
C 跨文件分析测试
验证 C 引擎的 NewFunction (code=5) → NewCore 链路

场景：
  22a/22b: 基本跨文件封装 sink（system / sprintf / fopen）
  23a/23b/23c: 多层函数调用封装（processInput → runCommand → system）
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Kunlun_M.settings')

import django
django.setup()

import pytest

TEST_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'c')

ALL_FILES_22 = [
    '22a_cross_file_exec_utils.c',
    '22b_cross_file_exec_main.c',
]

ALL_FILES_23 = [
    '23a_cross_file_multifunc_middle.c',
    '23b_cross_file_multifunc_utils.c',
    '23c_cross_file_multifunc_main.c',
]


def _scan_single_e2e(lang, file_list, vul_dir, svid=1, match='system'):
    """端到端 scan_single 测试辅助函数"""
    from core.scanner import scan_single
    from core.pretreatment import ast_object as ao

    # 清理全局状态
    ao.pre_result = {}
    ao.define_dict = {}

    ext_map = {
        'javascript': '.js', 'php': '.php', 'python': '.py',
        'java': '.java', 'go': '.go', 'c': '.c', 'solidity': '.sol',
    }
    ext = ext_map.get(lang, f'.{lang}')

    runtime_files = [(ext, {'list': file_list})]
    ao.init_pre(vul_dir, runtime_files)
    ao.pre_ast_all([lang])

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
        match=match,
        match_name=None,
        black_list=None,
        unmatch=None,
        vul_function=None,
        keyword=None,
        main=lambda regex_string: True,
    )

    file_list_parsed = [(ext, {'list': file_list})]
    return scan_single(vul_dir, rule, file_list_parsed, language=lang)


def test_c_scan_parser_code5_newfunction():
    """单元测试：22a scan_parser 应返回 code=5 (NewFunction)

    22a 中 system(cmd) — cmd 是 executeCommand 的形参 → code=5
    """
    from core.core_engine.c.parser import scan_parser as c_scan_parser
    from core.pretreatment import ast_object as ao

    # 清理全局状态
    ao.pre_result = {}
    ao.define_dict = {}

    utils_file = os.path.join(TEST_DIR, '22a_cross_file_exec_utils.c')
    runtime_files = [('.c', {'list': ['22a_cross_file_exec_utils.c']})]
    ao.init_pre(TEST_DIR, runtime_files)
    ao.pre_ast_all(['c'])

    # system 在第11行
    result = c_scan_parser(['system'], 11, utils_file)
    print(f"[22a] scan_parser result codes = {[r.get('code') for r in (result or [])]}")
    assert result and len(result) > 0, "scan_parser 应有结果"

    has_code5 = any(r.get('code') == 5 for r in result)
    assert has_code5, f"应有 code=5 (NewFunction): {[r.get('code') for r in result]}"

    # 检查 chain 中有 NewFunction 标记
    code5_result = [r for r in result if r.get('code') == 5][0]
    chain = code5_result.get('chain', [])
    has_newfunc = any(isinstance(c, tuple) and len(c) >= 1 and c[0] == 'NewFunction' for c in chain)
    assert has_newfunc, f"chain 中应有 NewFunction: {chain}"

    print(f"[22a] ✅ code=5 + NewFunction chain 正确生成: {chain}")


def test_c_e2e_cross_file_exec():
    """端到端测试：22a/22b system() 跨文件封装"""
    results = _scan_single_e2e('c', ALL_FILES_22, TEST_DIR)
    print(f"[e2e-22] results = {results}")
    assert results is not None, "scan_single 应返回结果"
    assert len(results) > 0, "22a/22b 应检出至少 1 个漏洞"
    print(f"[e2e-22] ✅ 端到端检出 {len(results)} 个漏洞")


def test_c_e2e_multifunc_cross_file():
    """端到端测试：23a/23b/23c 多层函数调用封装"""
    results = _scan_single_e2e('c', ALL_FILES_23, TEST_DIR)
    print(f"[e2e-23] results = {results}")
    assert results is not None and len(results) > 0, "23a/23b/23c 应检出至少 1 个漏洞"
    print(f"[e2e-23] ✅ 端到端检出 {len(results)} 个漏洞")


def main():
    """手动运行所有测试"""
    print("=" * 60)
    print("C 跨文件分析 Benchmark (NewCore code=5)")
    print("=" * 60)

    tests = [
        ("scan_parser code=5", test_c_scan_parser_code5_newfunction),
        ("端到端 22a/22b system()", test_c_e2e_cross_file_exec),
        ("端到端 23a/23b/23c 多层函数", test_c_e2e_multifunc_cross_file),
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
