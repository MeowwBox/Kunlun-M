#!/usr/bin/env python3
"""C NewCore benchmark test runner.

Tests that C NewFunction (code=5) correctly triggers NewCore second-pass
scanning for cross-file wrapped sink functions.

Usage:
    cd /path/to/Kunlun-M
    source /path/to/venv/bin/activate
    python tests/c/run_newcore_tests.py
"""
import json
import os
import shutil
import subprocess
import sys
import time

_repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
test_dir = os.path.join(_repo_root, 'tests', 'c')
ci_scan = os.path.join(_repo_root, 'tools', 'ci_scan.py')
output_dir = os.path.join(test_dir, '_newcore_output')

# (main_file, language, should_detect, description, expected_cvis)
# C NewCore: cross-file wrapper functions
test_cases = [
    # 25: 单层跨文件封装 - 命令注入
    ('25b_newfunc_exec_main.c', 'c', True, '跨文件 executeCommand(argv[1]) -> system',
     ['CVI-9001']),
    # 26: 单层跨文件封装 - 格式化字符串
    ('26b_newfunc_sqli_main.c', 'c', True, '跨文件 logMessage(getenv) -> sprintf',
     ['CVI-9002']),
    # 27: 单层跨文件封装 - 路径穿越
    ('27b_newfunc_path_main.c', 'c', True, '跨文件 readConfig(argv[1]) -> fopen',
     ['CVI-9004']),
    # 28: 跨文件返回值
    ('28b_newfunc_return_main.c', 'c', True, '跨文件 readInput() -> strcpy+system',
     ['CVI-9001', 'CVI-9003']),
    # 29: 多 sink 封装
    ('29b_newfunc_multi_main.c', 'c', True, '跨文件 multi wrapper: runCommand+loadFile+formatOutput',
     ['CVI-9001', 'CVI-9002', 'CVI-9004']),
]


def run_scan(test_file):
    """Run ci_scan on a single file and return JSON results."""
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, os.path.basename(test_file) + '.json')

    cmd = [
        sys.executable, ci_scan,
        '--language', 'c',
        '--file', os.path.join(test_dir, test_file),
        '--output', out_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=_repo_root)
        if result.returncode != 0:
            print(f"  [STDERR] {result.stderr.strip()[:300]}")
            return None
        if os.path.exists(out_path):
            with open(out_path) as f:
                return json.load(f)
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] scan exceeded 120s")
    except Exception as e:
        print(f"  [ERROR] {e}")
    return None


def extract_vulns(results):
    """Extract list of CVI IDs from scan results."""
    if not results:
        return []
    vulns = []
    # ci_scan output format: list of vulnerability dicts
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict):
                cvi = item.get('cvi') or item.get('vuln_class') or item.get('vulnerability_type') or ''
                if 'CVI' in str(cvi):
                    vulns.append(str(cvi))
    elif isinstance(results, dict):
        # might have 'results' or 'vulnerabilities' key
        for key in ('results', 'vulnerabilities', 'data'):
            if key in results:
                inner = results[key]
                if isinstance(inner, list):
                    for item in inner:
                        if isinstance(item, dict):
                            cvi = item.get('cvi') or item.get('vuln_class') or item.get('vulnerability_type') or ''
                            if 'CVI' in str(cvi):
                                vulns.append(str(cvi))
    return vulns


def main():
    print("=" * 70)
    print("C NewCore Benchmark Test")
    print("=" * 70)

    os.makedirs(output_dir, exist_ok=True)
    passed = 0
    failed = 0
    errors = 0

    for test_file, lang, should_detect, desc, expected_cvis in test_cases:
        print(f"\n[{test_file}] {desc}")
        print(f"  Expected: detect={should_detect}, CVIs={expected_cvis}")

        results = run_scan(test_file)

        if results is None:
            print(f"  Result: ERROR (scan failed)")
            errors += 1
            continue

        vulns = extract_vulns(results)
        detected = len(vulns) > 0

        if should_detect:
            # Check expected CVIs are all present
            found_cvis = set(vulns)
            missing = set(expected_cvis) - found_cvis
            if not missing:
                print(f"  Result: PASS (detected {vulns})")
                passed += 1
            else:
                print(f"  Result: FAIL (detected {vulns}, missing {missing})")
                failed += 1
        else:
            if detected:
                print(f"  Result: FAIL (false positive: {vulns})")
                failed += 1
            else:
                print(f"  Result: PASS (correctly not detected)")
                passed += 1

        # Debug: print raw results structure
        if should_detect and not detected:
            print(f"  [DEBUG] Raw results type: {type(results)}")
            if isinstance(results, list):
                print(f"  [DEBUG] List length: {len(results)}")
                if results:
                    print(f"  [DEBUG] First item keys: {list(results[0].keys()) if isinstance(results[0], dict) else results[0]}")
            elif isinstance(results, dict):
                print(f"  [DEBUG] Dict keys: {list(results.keys())}")
                for k, v in results.items():
                    if isinstance(v, list) and v:
                        print(f"  [DEBUG] {k}: list len={len(v)}")
                        if isinstance(v[0], dict):
                            print(f"  [DEBUG]   first item keys: {list(v[0].keys())}")
                            print(f"  [DEBUG]   first item: {json.dumps(v[0], ensure_ascii=False)[:300]}")
                    elif not isinstance(v, (list, dict)):
                        print(f"  [DEBUG] {k}: {str(v)[:200]}")

    print(f"\n{'=' * 70}")
    print(f"Results: {passed} passed, {failed} failed, {errors} errors out of {len(test_cases)}")
    print(f"{'=' * 70}")

    return 0 if (failed == 0 and errors == 0) else 1


if __name__ == '__main__':
    sys.exit(main())
