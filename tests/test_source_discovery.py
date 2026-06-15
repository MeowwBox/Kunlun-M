#!/usr/bin/env python3
"""测试 Source Discovery 修复：验证只标记 return 值包含 source 的函数"""
import sys, os, importlib.util

PROJECT = '/home/ubuntu/.hermes/hermes-agent/Kunlun-M'
sys.path.insert(0, PROJECT)

def load_module(lang):
    mod_path = os.path.join(PROJECT, 'core', 'core_engine', lang, 'source_discovery.py')
    spec = importlib.util.spec_from_file_location(f'source_discovery_{lang}', mod_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

tests_passed = 0
tests_failed = 0

def check(name, actual, expected):
    global tests_passed, tests_failed
    status = "✅" if actual == expected else "❌"
    if actual == expected:
        tests_passed += 1
    else:
        tests_failed += 1
    print(f"  {status} {name}: actual={actual}, expected={expected}")

# =============================================
# PHP 测试 — 用 lphply 构造 AST 节点
# =============================================
print("=" * 60)
print("PHP Source Discovery 测试")
print("=" * 60)

php_sd = load_module('php')
from phply import phpast as php

# 构造两个函数体的 body_nodes:
# getConfig: 函数体内有 $_GET 但 return 是 $this->config（不包含 source）
# getRawInput: return $_GET['raw']（包含 source）
# noReturn: 有 $_GET 但没有 return
# mixedReturn: 有一个分支 return $_POST['data']

def php_body_contains_test(body_nodes, registry):
    """直接调用 _function_body_contains_source"""
    return php_sd._function_body_contains_source(body_nodes, registry)

registry = php_sd.SourceRegistry()
registry.builtin_sources.add('$_GET')
registry.builtin_sources.add('$_POST')

# getConfig: body 有 $_GET 访问，但 return 值不包含 source
getConfig_body = [
    php.Assignment(
        left=php.Variable(name='debug'),
        expr=php.ArrayOffset(node=php.Variable(name='$_GET'), offset=php.Constant(value='debug')),
        lineno=2
    ),
    php.Return(node=php.ObjectProperty(node=php.Variable(name='this'), name='config'), lineno=3),
]
check('getConfig body (return $this->config)', php_body_contains_test(getConfig_body, registry), False)

# getRawInput: return $_GET['raw']
getRawInput_body = [
    php.Return(node=php.ArrayOffset(node=php.Variable(name='$_GET'), offset=php.Constant(value='raw')), lineno=2),
]
check('getRawInput body (return $_GET)', php_body_contains_test(getRawInput_body, registry), True)

# noReturn: 无 return 语句
noReturn_body = [
    php.Assignment(
        left=php.Variable(name='x'),
        expr=php.ArrayOffset(node=php.Variable(name='$_GET'), offset=php.Constant(value='x')),
        lineno=2
    ),
    php.Echo(node=php.Variable(name='x'), lineno=3),
]
check('noReturn body (无 return)', php_body_contains_test(noReturn_body, registry), False)

# mixedReturn: return 在嵌套的 If 节点中
mixedReturn_body = [
    php.If(
        expr=php.Variable(name='cond'),
        body=[
            php.Return(node=php.ObjectProperty(node=php.Variable(name='this'), name='safe'), lineno=3),
        ],
        elsif=[],
        else_=[
            php.Return(node=php.ArrayOffset(node=php.Variable(name='$_POST'), offset=php.Constant(value='data')), lineno=5),
        ],
        lineno=2
    ),
]
check('mixedReturn body (return $_POST 在 else 分支)', php_body_contains_test(mixedReturn_body, registry), True)

# =============================================
# JavaScript 测试
# =============================================
print("\n" + "=" * 60)
print("JavaScript Source Discovery 测试")
print("=" * 60)

js_sd = load_module('javascript')

# 用 esprima 解析
import esprima

js_cases = {
    'getConfig': """function getConfig() {
        const debug = req.query.debug;
        return this.config;
    }""",
    'getRawInput': """function getRawInput() {
        return req.body.raw;
    }""",
    'noReturn': """function noReturn() {
        const x = req.query.x;
        console.log(x);
    }""",
    'mixedReturn': """function mixedReturn(cond) {
        if (cond) { return this.safe; }
        return req.body.data;
    }""",
}

js_registry = js_sd.SourceRegistry()
js_registry.source_members.add('req.query')
js_registry.source_members.add('req.body')

for name, code in js_cases.items():
    tree = esprima.parse(code, loc=True)
    body_stmts = tree.body[0].body.body  # FunctionDeclaration.body.body
    result = js_sd._function_body_contains_source(body_stmts, js_registry)
    expected = name in ('getRawInput', 'mixedReturn')
    check(f'{name}', result, expected)

# =============================================
# Python 测试
# =============================================
print("\n" + "=" * 60)
print("Python Source Discovery 测试")
print("=" * 60)

import ast
py_sd = load_module('python')

py_code = """
def get_config():
    debug = request.args.get('debug')
    return self.config

def get_raw_input():
    return request.args.get('raw')

def no_return():
    x = request.args.get('x')
    print(x)

def mixed_return(cond):
    if cond:
        return self.safe
    return request.form.get('data')
"""

py_tree = ast.parse(py_code)
py_registry = py_sd.SourceRegistry()
py_registry.source_members.add('request.args')
py_registry.source_members.add('request.form')

py_sd._walk_for_functions(py_tree, 'test.py', py_registry)

print(f"\n标记的 source producer: {list(py_registry.user_source_functions.keys())}")
check('get_config (return 和 source 无关)', 'get_config' in py_registry.user_source_functions, False)
check('get_raw_input (return request.args)', 'get_raw_input' in py_registry.user_source_functions, True)
check('no_return (无 return)', 'no_return' in py_registry.user_source_functions, False)
check('mixed_return (有 return source)', 'mixed_return' in py_registry.user_source_functions, True)

# =============================================
# Go 测试
# =============================================
print("\n" + "=" * 60)
print("Go Source Discovery 测试")
print("=" * 60)

go_sd = load_module('go')
import tree_sitter_go as tsgo
from tree_sitter import Language, Parser
GO_PARSER = Parser(Language(tsgo.language()))

go_code = """
package main

import "os"

func getConfig() string {
    debug := os.Getenv("DEBUG")
    return "config_value"
}

func getRawInput() string {
    return os.Getenv("RAW_INPUT")
}

func noReturn() {
    x := os.Getenv("X")
    println(x)
}

func mixedReturn(cond bool) string {
    if cond {
        return "safe"
    }
    return os.Getenv("MIXED")
}
"""

go_tree = GO_PARSER.parse(go_code.encode())
go_registry = go_sd.SourceRegistry()
go_registry.source_members.add('os.Getenv')

go_sd._walk_for_functions(go_tree.root_node, 'test.go', go_registry)

print(f"\n标记的 source producer: {list(go_registry.user_source_functions.keys())}")
check('getConfig (return 和 source 无关)', 'getConfig' in go_registry.user_source_functions, False)
check('getRawInput (return os.Getenv)', 'getRawInput' in go_registry.user_source_functions, True)
check('noReturn (无 return)', 'noReturn' in go_registry.user_source_functions, False)
check('mixedReturn (有 return os.Getenv)', 'mixedReturn' in go_registry.user_source_functions, True)

# =============================================
# C 测试
# =============================================
print("\n" + "=" * 60)
print("C Source Discovery 测试")
print("=" * 60)

c_sd = load_module('c')
import tree_sitter_c as tsc
C_PARSER = Parser(Language(tsc.language()))

c_code = """
const char* getConfig() {
    char* debug = getenv("DEBUG");
    return "config_value";
}

const char* getRawInput() {
    return getenv("RAW_INPUT");
}

void noReturn() {
    char* x = getenv("X");
    printf("%s", x);
}

const char* mixedReturn(int cond) {
    if (cond) {
        return "safe";
    }
    return getenv("MIXED");
}
"""

c_tree = C_PARSER.parse(c_code.encode())
c_registry = c_sd.SourceRegistry()
c_registry.source_members.add('getenv')

c_sd._walk_for_functions(c_tree.root_node, 'test.c', c_registry)

print(f"\n标记的 source producer: {list(c_registry.user_source_functions.keys())}")
check('getConfig (return 和 source 无关)', 'getConfig' in c_registry.user_source_functions, False)
check('getRawInput (return getenv)', 'getRawInput' in c_registry.user_source_functions, True)
check('noReturn (无 return)', 'noReturn' in c_registry.user_source_functions, False)
check('mixedReturn (有 return getenv)', 'mixedReturn' in c_registry.user_source_functions, True)

# =============================================
# 总结
# =============================================
print("\n" + "=" * 60)
print(f"总计: {tests_passed} passed, {tests_failed} failed")
if tests_failed == 0:
    print("全部通过 ✅")
else:
    print(f"有 {tests_failed} 个失败 ❌")
    sys.exit(1)
print("=" * 60)
