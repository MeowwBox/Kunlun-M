#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Python AST Parser — Python 反向污点追踪引擎
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :author:    LoRexxar <LoRexxar@gmail.com>
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""
import sys
sys.setrecursionlimit(3000)
import ast
import os
import re
import traceback

from utils.log import logger
from core.pretreatment import ast_object as _ast_object_singleton
from core.core_engine.trace_cache import TraceCache
from core.core_engine.branch_constraint import BranchConstraint
from core.core_engine.python.builtin_knowledge import lookup as lookup_builtin
from core.core_engine.python.summary_generator import lookup_summary
from core.core_engine.python.source_discovery import SourceRegistry, discover_sources

# 全局状态（与 PHP/Java parser 保持一致的模式）
scan_results = []
is_repair_functions = []
is_controlled_params = []
scan_chain = []
# 行号通过函数返回值三元组 (code, source, source_lineno) 传递

# 函数摘要系统状态
_summaries_initialized = False
_file_summaries = {}

# 内置敏感函数列表（用于跨文件间接 sink 检测）
BUILTIN_SENSITIVE_SINKS = [
    'os.system', 'os.popen', 'os.spawnl', 'os.spawnlp', 'os.spawnv', 'os.spawnve',
    'subprocess.call', 'subprocess.run', 'subprocess.Popen', 'subprocess.check_output',
    'subprocess.check_call',
    'eval', 'exec', 'compile',
    'pickle.loads', 'pickle.load', 'yaml.load', 'yaml.unsafe_load',
    'requests.get', 'requests.post', 'requests.put', 'requests.delete',
    'urllib.request.urlopen', 'urllib.request.urlretrieve',
    'open', 'file',
    'socket.connect', 'socket.send',
]


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------
# 模块级追踪去重集合，防止 parameters_back 循环递归
_trace_visited = set()

# 追踪缓存 + 内置知识库
_trace_cache = TraceCache("python")
_source_registry = None

def _parse_imports(tree, file_path):
    """解析 AST 中的 import 语句，返回 {imported_name: module_file_path} 映射
    
    支持:
      from helpers import run_command  →  {'run_command': '/path/helpers.py'}
      import helpers                   →  {'helpers': '/path/helpers.py'}
      from pkg.helpers import func     →  {'func': '/path/pkg/helpers.py'}
    """
    import_map = {}
    base_dir = os.path.dirname(file_path)
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module_name = node.module or ''
            # 尝试将模块名转换为文件路径
            module_path = _resolve_module_path(module_name, base_dir)
            if module_path:
                for alias in node.names:
                    name = alias.asname or alias.name
                    import_map[name] = module_path
                    
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name
                module_path = _resolve_module_path(name, base_dir)
                if module_path:
                    import_map[name] = module_path
    
    return import_map


def _resolve_module_path(module_name, base_dir):
    """尝试将 Python 模块名解析为文件路径"""
    parts = module_name.split('.')
    # 尝试 as file: base_dir/part1/part2/.../partN.py
    candidate = os.path.join(base_dir, *parts[:-1], parts[-1] + '.py') if parts else None
    if candidate and os.path.isfile(candidate):
        return os.path.normpath(candidate)
    # 尝试 as package: base_dir/part1/.../partN/__init__.py
    candidate = os.path.join(base_dir, *parts, '__init__.py')
    if os.path.isfile(candidate):
        return os.path.normpath(candidate)
    return None


def _resolve_variable_type(tree, var_name, target_line, import_map):
    """尝试推断变量的类型名（用于跨文件类方法追踪）
    
    ex = Executor(base) → 返回 'Executor'
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                tname = _get_name(t)
                if tname == var_name and isinstance(node.value, ast.Call):
                    # ex = Executor(...)
                    if isinstance(node.value.func, ast.Name):
                        return node.value.func.id
                    elif isinstance(node.value.func, ast.Attribute):
                        return node.value.func.attr
    return None


def _get_call_name(node):
    """从 ast.Call 节点提取完整函数调用名，如 os.system, subprocess.call, eval"""
    if not isinstance(node, ast.Call):
        return None

    func = node.func

    # direct call: eval(...)
    if isinstance(func, ast.Name):
        return func.id

    # attribute call: os.system(...), subprocess.call(...)
    if isinstance(func, ast.Attribute):
        parts = []
        current = func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        parts.reverse()
        return '.'.join(parts)

    return None


def _get_name(node):
    """从 AST 节点提取变量名（支持 Name, Attribute, Subscript 等）"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _get_name(node.value)
        if base:
            return '{}.{}'.format(base, node.attr)
    if isinstance(node, ast.Subscript):
        return _get_name(node.value)
    if isinstance(node, ast.Starred):
        return _get_name(node.value)
    return None


def _contains_name(node, name):
    """检查 AST 节点（表达式）是否包含指定名称的变量"""
    if node is None:
        return False

    if isinstance(node, ast.Name):
        return node.id == name

    if isinstance(node, ast.BinOp):
        return _contains_name(node.left, name) or _contains_name(node.right, name)

    if isinstance(node, ast.BoolOp):
        return any(_contains_name(v, name) for v in node.values)

    if isinstance(node, ast.Compare):
        return _contains_name(node.left, name) or any(_contains_name(c, name) for c in node.comparators)

    if isinstance(node, ast.UnaryOp):
        return _contains_name(node.operand, name)

    if isinstance(node, ast.Call):
        # 检查函数名和参数
        if _contains_name(node.func, name):
            return True
        return any(_contains_name(arg, name) for arg in (node.args or []))

    if isinstance(node, ast.Attribute):
        return _contains_name(node.value, name)

    if isinstance(node, ast.Subscript):
        return _contains_name(node.value, name) or _contains_name(node.slice, name)

    if isinstance(node, ast.IfExp):
        return (_contains_name(node.test, name) or
                _contains_name(node.body, name) or
                _contains_name(node.orelse, name))

    if isinstance(node, ast.Lambda):
        # 不进入 lambda 体内搜索外部变量
        return False

    if isinstance(node, ast.JoinedStr):
        # f-string
        return any(_contains_name(v, name) for v in node.values
                    if isinstance(v, ast.FormattedValue))

    if isinstance(node, ast.FormattedValue):
        return _contains_name(node.value, name)

    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        return any(_contains_name(elt, name) for elt in node.elts)

    if isinstance(node, ast.Dict):
        return (any(_contains_name(k, name) for k in (node.keys or []) if k) or
                any(_contains_name(v, name) for v in (node.values or [])))

    if isinstance(node, ast.Starred):
        return _contains_name(node.value, name)

    if isinstance(node, ast.Constant):
        return False

    return False


def _collect_names_from_str(expr_str):
    """从字符串表达式（_expr_to_str 的输出）中提取变量名
    
    简单实现：按非标识符字符分割，过滤掉关键字和常量。
    """
    import keyword
    parts = re.split(r'[^a-zA-Z_][a-zA-Z0-9_]*', expr_str)
    # 更精确：提取所有标识符
    identifiers = set(re.findall(r'[a-zA-Z_][a-zA-Z0-9_.]*', expr_str))
    # 过滤关键字和常见常量
    skip = {'None', 'True', 'False', 'str', 'int', 'float', 'list', 'dict', 'tuple',
            'set', 'bytes', 'bool', 'type', 'super', 'print', 'len', 'range'}
    return identifiers - skip - set(keyword.kwlist)


def _collect_names(node, names=None, _depth=0):
    """递归收集表达式中所有变量名"""
    if names is None:
        names = set()

    if node is None or _depth > 20:
        return names

    if isinstance(node, ast.Name):
        names.add(node.id)

    elif isinstance(node, ast.BinOp):
        _collect_names(node.left, names, _depth+1)
        _collect_names(node.right, names, _depth+1)

    elif isinstance(node, ast.BoolOp):
        for v in node.values:
            _collect_names(v, names, _depth+1)

    elif isinstance(node, ast.UnaryOp):
        _collect_names(node.operand, names, _depth+1)

    elif isinstance(node, ast.Call):
        _collect_names(node.func, names, _depth+1)
        for arg in (node.args or []):
            _collect_names(arg, names, _depth+1)
        for kw in (node.keywords or []):
            _collect_names(kw.value, names, _depth+1)

    elif isinstance(node, ast.Attribute):
        # 保留完整属性名（如 self.base, obj.attr），而不是只取 value
        full_name = _get_name(node)
        if full_name:
            names.add(full_name)
        # 同时递归收集基础变量名（如 myFile.name → 也收集 myFile）
        _collect_names(node.value, names, _depth+1)

    elif isinstance(node, ast.Subscript):
        _collect_names(node.value, names, _depth+1)
        _collect_names(node.slice, names, _depth+1)

    elif isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        for elt in node.elts:
            _collect_names(elt, names, _depth+1)

    elif isinstance(node, ast.JoinedStr):
        for v in node.values:
            if isinstance(v, ast.FormattedValue):
                _collect_names(v.value, names, _depth+1)

    elif isinstance(node, ast.IfExp):
        _collect_names(node.test, names, _depth+1)
        _collect_names(node.body, names, _depth+1)
        _collect_names(node.orelse, names, _depth+1)

    elif isinstance(node, ast.Dict):
        for k in (node.keys or []):
            if k:
                _collect_names(k, names, _depth+1)
        for v in (node.values or []):
            _collect_names(v, names, _depth+1)

    return names


def _expr_to_str(node):
    """将 AST 表达式转为可读字符串（简化版）"""
    if node is None:
        return ''
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Attribute):
        base = _expr_to_str(node.value)
        return '{}.{}'.format(base, node.attr) if base else node.attr
    if isinstance(node, ast.Call):
        # 递归展开链式调用：request.body.decode(...).encode(...) → request.body.decode(...).encode(...)
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Call):
            return '{}.{}(...)'.format(_expr_to_str(func.value), func.attr)
        return '{}(...)'.format(_get_call_name(node) or '...')
    if isinstance(node, ast.BinOp):
        return '{} + {}'.format(_expr_to_str(node.left), _expr_to_str(node.right))
    if isinstance(node, ast.Subscript):
        return '{}[...]'.format(_expr_to_str(node.value))
    return ast.dump(node)[:80]


# ---------------------------------------------------------------------------
# 污点判断
# ---------------------------------------------------------------------------

def is_controllable(expr_str, controlled_params=None):
    """检查表达式字符串是否包含可控输入源"""
    if controlled_params is None:
        controlled_params = is_controlled_params

    if not controlled_params:
        return False

    for cp in controlled_params:
        if cp in expr_str:
            return True
        # 特殊处理：可控源是 func() 形式，匹配显式调用 func(...)
        if cp.endswith('()'):
            func_name = cp[:-2]
            if expr_str.startswith(func_name + '('):
                return True

    return False


def is_repair(expr_str, repair_functions=None):
    """检查表达式字符串是否包含修复函数"""
    if repair_functions is None:
        repair_functions = is_repair_functions

    if not repair_functions:
        return False

    for rf in repair_functions:
        if rf in expr_str:
            return True
    return False


# ---------------------------------------------------------------------------
# 核心反向追踪
# ---------------------------------------------------------------------------

def parameters_back(param_name, nodes, vul_lineno, file_path,
                     repair_functions=None, controlled_params=None,
                     visited_funcs=None, depth=0):
    """
    从 vul_lineno 行向上遍历 AST 节点，反向追踪 param_name 的数据流来源。

    返回值:
        1  — 可控（污点到达用户输入源）
        2  — 已修复（经过修复函数处理）
        3  — 未确认
        4  — 新漏洞函数（追踪到函数参数，需要生成新规则）
        5  — global 变量
        -1 — 不可控
    """
    if repair_functions is None:
        repair_functions = is_repair_functions
    if controlled_params is None:
        controlled_params = is_controlled_params
    if visited_funcs is None:
        visited_funcs = set()

    if depth > 5:
        return -1, None, 0

    # 查缓存
    if vul_lineno and file_path:
        cached = _trace_cache.get(file_path, param_name, vul_lineno)
        if cached is not None:
            return cached

    tree = _ast_object_singleton.get_nodes(file_path)
    if not tree or not hasattr(tree, 'body'):
        return -1, None, 0

    # 收集 vul_lineno 之前的所有顶层语句
    all_stmts = tree.body
    relevant_stmts = [s for s in all_stmts
                       if hasattr(s, 'lineno') and s.lineno <= int(vul_lineno)]

    # 找到包含 vul_lineno 的函数（如果有的话）
    func_node = _find_function_at_line(tree, int(vul_lineno))

    if func_node:
        # 在函数内追踪
        result = _trace_in_function(param_name, func_node, int(vul_lineno),
                                   file_path, repair_functions, controlled_params,
                                   visited_funcs, depth, tree)
    else:
        # 模块级别追踪
        result = _trace_in_stmts(param_name, relevant_stmts, int(vul_lineno),
                                file_path, repair_functions, controlled_params,
                                visited_funcs, depth, tree)

    # 写入缓存（只缓存确定性结果，跳过中间状态）
    if vul_lineno and file_path and result is not None:
        code = result[0] if not isinstance(result[0], str) else -1
        if code in (-1, 1, 2):
            _trace_cache.put(file_path, param_name, int(vul_lineno), result)

    return result


def _find_function_at_line(tree, target_line):
    """找到包含目标行号的函数定义"""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if hasattr(node, 'lineno') and hasattr(node, 'end_lineno') and node.end_lineno:
                if node.lineno <= target_line <= node.end_lineno:
                    return node
            elif hasattr(node, 'lineno') and node.lineno <= target_line:
                # fallback: 没有 end_lineno，估算到下一个同级节点
                return node
    return None


def _find_class_at_line(tree, target_line):
    """找到包含目标行号的类定义"""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if hasattr(node, 'lineno') and hasattr(node, 'end_lineno') and node.end_lineno:
                if node.lineno <= target_line <= node.end_lineno:
                    return node
    return None


def _find_class_containing_method(tree, method_node):
    """找到包含指定方法的类定义"""
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if item is method_node:
                    return node
    return None


def _trace_self_attribute(attr_name, class_node, vul_lineno, file_path,
                           repair_functions, controlled_params,
                           visited_funcs, depth, tree):
    """追踪 self.xxx 属性的来源
    
    在类的 __init__ 方法中查找 self.xxx = expr 赋值，
    然后追踪 expr 的来源（通常是构造函数参数）。
    
    返回值同 parameters_back: (code, source)
    """
    # 提取属性名（去掉 self. 前缀）
    # attr_name = 'self.base' → attr = 'base'
    if not attr_name.startswith('self.'):
        return None
    attr = attr_name[5:]  # 去掉 'self.'

    # 在类中查找 __init__ 方法
    init_method = None
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == '__init__':
            init_method = item
            break

    if not init_method:
        # 当前类没有 __init__，检查父类
        for base in class_node.bases:
            base_name = _get_name(base)
            if base_name:
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == base_name:
                        for item in node.body:
                            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == '__init__':
                                init_method = item
                                break
                        if init_method:
                            break
                if init_method:
                    break

    if not init_method:
        # 没有任何 __init__（含父类），检查类级别属性
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for t in item.targets:
                    if _get_name(t) == attr_name:
                        return _trace_expr(attr_name, item.value, item.lineno, file_path,
                                            repair_functions, controlled_params,
                                            visited_funcs, depth, tree)
        return None

    # 在 __init__ 体内查找 self.attr = expr
    for stmt in init_method.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                target_name = _get_name(target)
                if target_name == attr_name:
                    logger.debug("[AST][Python] Tracing self attribute: {} = expr at L{}".format(
                        attr_name, stmt.lineno))
                    # 追踪右部表达式
                    result = _trace_expr(attr_name, stmt.value, stmt.lineno, file_path,
                                          repair_functions, controlled_params,
                                          visited_funcs, depth, tree)
                    if result and result[0] != -1:
                        return result
                    # 如果 _trace_expr 返回 -1 或 None，检查右部是否是构造函数参数
                    rhs_name = _get_name(stmt.value)
                    if rhs_name:
                        # 检查是否是 __init__ 的参数（排除 self）
                        for arg in init_method.args.args:
                            if arg.arg == rhs_name and arg.arg != 'self':
                                logger.debug("[AST][Python] self.{} comes from __init__ param {}".format(
                                    attr, rhs_name))
                                return 4, init_method, vul_lineno

    # 如果 __init__ 中没找到赋值，检查是否有 @property 方法
    # 支持类继承：先在当前类找，找不到去父类找
    attr = attr_name[5:]  # 去掉 'self.' 前缀
    classes_to_check = [class_node]
    # 收集父类
    for base in class_node.bases:
        base_name = _get_name(base)
        if base_name:
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == base_name:
                    classes_to_check.append(node)
                    break

    for check_class in classes_to_check:
        for item in check_class.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == attr:
                # 检查是否被 @property 装饰
                for dec in item.decorator_list:
                    dec_name = _get_name(dec) if dec else None
                    if dec_name == 'property':
                        logger.debug("[AST][Python] self.{} is @property (in {}), tracing getter".format(
                            attr, check_class.name))
                        return _trace_property_getter(item, vul_lineno, file_path,
                                                       repair_functions, controlled_params,
                                                       visited_funcs, depth, tree)

    return None


def _trace_property_getter(prop_func, vul_lineno, file_path,
                            repair_functions, controlled_params,
                            visited_funcs, depth, tree):
    """追踪 @property getter 的返回值是否可控
    
    在 getter 内找到 return 语句，追踪返回值表达式。
    如果返回值包含 self.xxx，递归追踪到 __init__。
    """
    # 收集 getter 体内的赋值关系（与 _trace_function_return 类似）
    # 但 @property 通常无参数（除了 self），所以主要追踪 self.xxx 属性
    for node in ast.walk(prop_func):
        if isinstance(node, ast.Return) and node.value:
            # 追踪返回值表达式
            result = _trace_expr('return_value', node.value, 
                                  node.lineno if hasattr(node, 'lineno') else vul_lineno,
                                  file_path, repair_functions, controlled_params,
                                  visited_funcs, depth, tree)
            if result and result[0] in (1, 2, 4):
                return result
            
            # fallback: 收集 names，逐个追踪
            names = _collect_names(node.value)
            for name in names:
                result = parameters_back(name, [], 
                                          node.lineno if hasattr(node, 'lineno') else vul_lineno,
                                          file_path, repair_functions, controlled_params,
                                          visited_funcs, depth + 1)
                if result and result[0] in (1, 4):
                    return result
    
    return None


def _trace_in_function(param_name, func_node, vul_lineno, file_path,
                        repair_functions, controlled_params,
                        visited_funcs, depth, tree):
    """在函数体内追踪变量来源"""
    # 注意：不把当前函数名加入 visited_funcs
    # 因为同一函数内可能需要追踪多个变量的来源（如 full_cmd → arg）
    # visited_funcs 用于防止跨函数循环追踪，由 parameters_back 的调用者管理

    stmts = func_node.body
    return _trace_in_stmts(param_name, stmts, vul_lineno, file_path,
                            repair_functions, controlled_params,
                            visited_funcs, depth, tree,
                            func_node=func_node)


def _trace_in_stmts(param_name, stmts, vul_lineno, file_path,
                     repair_functions, controlled_params,
                     visited_funcs, depth, tree,
                     func_node=None):
    """在语句列表中反向追踪变量来源"""

    # 过滤出 vul_lineno 之前的语句，倒序遍历
    prior_stmts = []
    for s in stmts:
        if hasattr(s, 'lineno') and s.lineno <= vul_lineno:
            prior_stmts.append(s)

    for stmt in reversed(prior_stmts):
        result = _trace_stmt(param_name, stmt, vul_lineno, file_path,
                              repair_functions, controlled_params,
                              visited_funcs, depth, tree, func_node)
        if result is not None:
            # 处理函数返回的依赖变量：赋值右部是函数调用，返回值依赖调用者变量
            # 需要继续向上查找这些变量的更早赋值
            if isinstance(result, tuple) and len(result) >= 2 and result[0] == 'deps':
                dep_vars = result[1]
                logger.debug("[AST][Python] Assignment at line {} returns deps: {}, continuing upward trace".format(
                    stmt.lineno, dep_vars))
                # 对每个依赖变量，从当前赋值行之前继续追踪
                for dep_var in dep_vars:
                    for earlier_stmt in reversed(prior_stmts):
                        if hasattr(earlier_stmt, 'lineno') and earlier_stmt.lineno < stmt.lineno:
                            r = _trace_stmt(dep_var, earlier_stmt, stmt.lineno - 1, file_path,
                                             repair_functions, controlled_params,
                                             visited_funcs, depth, tree, func_node)
                            if r is not None:
                                if isinstance(r, tuple) and len(r) >= 2 and r[0] == 'deps':
                                    continue  # 依赖链太深，跳过
                                return r
                # 所有依赖变量都没找到可控来源，返回未确认
                return 3, None, vul_lineno
            return result

    # 如果在函数内且没找到赋值，检查是否是函数参数
    if func_node and isinstance(func_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for arg in func_node.args.args:
            if arg.arg == param_name:
                logger.debug("[AST][Python] Param {} is function argument of {}".format(
                    param_name, func_node.name))
                # 返回 code 4：新漏洞函数
                return 4, func_node, vul_lineno

    # 如果是 self.xxx 属性，到 __init__ 中查找赋值
    if func_node and param_name.startswith('self.'):
        class_node = _find_class_containing_method(tree, func_node)
        if class_node:
            attr_result = _trace_self_attribute(param_name, class_node, vul_lineno, file_path,
                                                  repair_functions, controlled_params,
                                                  visited_funcs, depth, tree)
            if attr_result is not None:
                return attr_result

    # 如果是 global 声明的变量
    if func_node:
        for s in func_node.body:
            if isinstance(s, ast.Global) and param_name in s.names:
                logger.debug("[AST][Python] Param {} is global variable".format(param_name))
                return 5, None, vul_lineno

    return -1, None, 0

def _find_sink_branch_py(if_stmt, vul_lineno):
    """判断 sink 行号位于 Python if/else 的哪个分支。返回 'if', 'else', 'outside'。"""
    if not vul_lineno:
        return 'outside'
    vul_lineno = int(vul_lineno)

    # if 体范围
    if if_stmt.body and int(if_stmt.body[0].lineno) <= vul_lineno <= int(if_stmt.body[-1].lineno):
        return 'if'

    # else/elif 体范围
    if if_stmt.orelse:
        # elif: orelse 是 [If] 节点
        if len(if_stmt.orelse) == 1 and isinstance(if_stmt.orelse[0], ast.If):
            return _find_sink_branch_py(if_stmt.orelse[0], vul_lineno)
        elif if_stmt.orelse and int(if_stmt.orelse[0].lineno) <= vul_lineno <= int(if_stmt.orelse[-1].lineno):
            return 'else'

    return 'outside'


# Python 类型验证方法 — x.isdigit() 等方法调用返回 true 时变量被约束为安全类型
_TYPE_CHECK_METHODS = frozenset({
    'isdigit', 'isnumeric', 'isdecimal',
    'isalpha', 'isalnum',
})


def _is_numeric_type_tuple(node):
    """检查 AST 节点是否为数值类型元组（如 (int, float)）"""
    if isinstance(node, ast.Tuple):
        return all(
            (isinstance(elt, ast.Name) and elt.id in ('int', 'float', 'complex', 'bool'))
            for elt in node.elts
        )
    # 单个类型：isinstance(x, int)
    if isinstance(node, ast.Name):
        return node.id in ('int', 'float', 'complex', 'bool')
    return False


def _is_strict_regex(pattern, is_fullmatch=False):
    """判断正则是否为严格全匹配模式（安全）。

    :param pattern: 正则字符串
    :param is_fullmatch: True 表示默认全匹配（如 re.fullmatch），不需要 ^...$ 锚定
    """
    if not pattern or not isinstance(pattern, str):
        return False

    if is_fullmatch:
        body = pattern
    else:
        if len(pattern) < 4:
            return False
        if not pattern.startswith('^') or not pattern.endswith('$'):
            return False
        body = pattern[1:-1]

    # 去掉转义的 \. 后检查是否含未转义的 .
    stripped = body.replace('\\.', '')
    if '.' in stripped:
        return False
    # 不含 * 或 ?（任意次数匹配）
    if '*' in stripped or '?' in stripped:
        return False
    return True


def extract_constraints_from_py_expr(expr):
    """
    从 Python 条件表达式中提取 BranchConstraint 列表。

    使用标准库 ast 模块的节点类型：
    - isinstance(x, type)    -> 类型约束（type_validated）
    - x.isdigit() / x.isalpha() -> 类型约束（type_validated）
    - re.match/r'^\\d+$', x / re.fullmatch(r'...', x) -> 正则约束（regex_validated）
    - x is None / x is not None -> 等值约束
    - x == value / x != value   -> 等值约束
    - x in list              -> 成员约束（简化：提取变量名，op='in'）
    - hasattr(x, attr)       -> 属性存在约束（暂不提取）
    - x and y               -> AND：两个约束都要满足
    - x or y                -> OR：忽略
    - not expr              -> 取反
    """
    if expr is None:
        return []

    constraints = []

    if isinstance(expr, ast.BoolOp):
        if isinstance(expr.op, ast.And):
            for val in expr.values:
                constraints.extend(extract_constraints_from_py_expr(val))
        elif isinstance(expr.op, ast.Or):
            # x == "a" or x == "b" 等价于 x in ["a", "b"]
            # 提取同一变量的枚举约束
            or_constraints = []
            for val in expr.values:
                or_constraints.extend(extract_constraints_from_py_expr(val))
            # 收集同一变量的所有 == 值
            from collections import defaultdict
            eq_values = defaultdict(list)
            for c in or_constraints:
                if c.op == '==' and c.var_name:
                    eq_values[c.var_name].append(c.value)
            for var_name, values in eq_values.items():
                if values:
                    constraints.append(BranchConstraint(
                        var_name=var_name, op='in',
                        value=values if len(values) > 1 else values[0]))
        return constraints

    if isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        inner = extract_constraints_from_py_expr(expr.operand)
        constraints = [c.negate() for c in inner]
        return constraints

    if isinstance(expr, ast.Compare):
        left = _get_name(expr.left)
        if left:
            for op, comparator in zip(expr.ops, expr.comparators):
                if isinstance(op, ast.Eq):
                    value = _extract_py_literal(comparator)
                    constraints.append(BranchConstraint(var_name=left, op='==', value=value))
                elif isinstance(op, ast.NotEq):
                    value = _extract_py_literal(comparator)
                    constraints.append(BranchConstraint(var_name=left, op='!=', value=value))
                elif isinstance(op, ast.Is):
                    # x is None
                    constraints.append(BranchConstraint(var_name=left, op='==', value=None))
                elif isinstance(op, ast.IsNot):
                    # x is not None
                    constraints.append(BranchConstraint(var_name=left, op='!=', value=None))
        return constraints

    if isinstance(expr, ast.Call):
        func_name = _get_call_name(expr)

        # isinstance(x, (int, float)) → x 被约束为数值类型
        if func_name == 'isinstance' and len(expr.args) >= 2:
            var_name = _get_name(expr.args[0])
            if var_name and _is_numeric_type_tuple(expr.args[1]):
                constraints.append(BranchConstraint(
                    var_name=var_name, op='type_validated', value='isinstance_numeric'))

        # x.isdigit() / x.isnumeric() 等方法调用
        elif isinstance(expr.func, ast.Attribute):
            var_name = _get_name(expr.func.value)
            method = expr.func.attr
            if var_name and method in _TYPE_CHECK_METHODS:
                constraints.append(BranchConstraint(
                    var_name=var_name, op='type_validated', value=method))

        # re.match(r'^\d+$', x) / re.fullmatch(r'...', x) — 严格正则
        if func_name in ('re.match', 're.fullmatch') and len(expr.args) >= 2:
            pattern = _extract_py_literal(expr.args[0])
            var_name = _get_name(expr.args[1])
            if var_name and pattern and isinstance(pattern, str):
                if _is_strict_regex(pattern, func_name == 're.fullmatch'):
                    constraints.append(BranchConstraint(
                        var_name=var_name, op='regex_validated', value=pattern))

    return constraints


def _extract_py_literal(node):
    """从 Python AST 节点提取字面量值。"""
    if isinstance(node, ast.Constant):
        return node.value
    return None


def _trace_stmt(param_name, stmt, vul_lineno, file_path,
                 repair_functions, controlled_params,
                 visited_funcs, depth, tree, func_node):
    """处理单个语句的追踪逻辑"""

    # --- 赋值语句: x = expr ---
    if isinstance(stmt, ast.Assign):
        for target in stmt.targets:
            target_name = _get_name(target)
            if target_name == param_name:
                # 找到赋值，追踪右部表达式
                return _trace_expr(param_name, stmt.value, stmt.lineno, file_path,
                                    repair_functions, controlled_params,
                                    visited_funcs, depth, tree)

    # --- 增量赋值: x += expr ---
    elif isinstance(stmt, ast.AugAssign):
        target_name = _get_name(stmt.target)
        if target_name == param_name:
            return _trace_expr(param_name, stmt.value, stmt.lineno, file_path,
                                repair_functions, controlled_params,
                                visited_funcs, depth, tree)

    # --- 注入赋值: x: type = expr ---
    elif isinstance(stmt, ast.AnnAssign) and stmt.value:
        target_name = _get_name(stmt.target)
        if target_name == param_name:
            return _trace_expr(param_name, stmt.value, stmt.lineno, file_path,
                                repair_functions, controlled_params,
                                visited_funcs, depth, tree)

    # --- with 语句: with open(...) as f ---
    elif isinstance(stmt, ast.With):
        for item in stmt.items:
            if item.optional_vars:
                var_name = _get_name(item.optional_vars)
                if var_name == param_name:
                    return _trace_expr(param_name, item.context_expr, stmt.lineno,
                                        file_path, repair_functions, controlled_params,
                                        visited_funcs, depth, tree)
        # 在 with 体内继续搜索
        result = _trace_in_stmts(param_name, stmt.body, vul_lineno, file_path,
                                  repair_functions, controlled_params,
                                  visited_funcs, depth, tree, func_node)
        if result and result[0] != -1:
            return result

    # --- if 语句 ---
    elif isinstance(stmt, ast.If):
        # 1. 判断 sink 在哪个分支
        sink_branch = _find_sink_branch_py(stmt, vul_lineno)
        logger.debug("[AST][Python] sink_branch={} for param {} lineno {}".format(sink_branch, param_name, vul_lineno))

        # 2. 提取当前分支的条件约束并确定分支体
        if sink_branch == 'if':
            constraints = extract_constraints_from_py_expr(stmt.test)
            body_stmts = stmt.body
        elif sink_branch == 'else':
            constraints = [c.negate() for c in extract_constraints_from_py_expr(stmt.test)]
            body_stmts = stmt.orelse if stmt.orelse else []
        else:
            # sink 在 if/else 之外 → 遍历所有分支找变量重赋值
            result = _trace_in_stmts(param_name, stmt.body, vul_lineno, file_path,
                                      repair_functions, controlled_params,
                                      visited_funcs, depth, tree, func_node)
            if result and result[0] in (1, 2, 3):
                return result
            if stmt.orelse:
                result = _trace_in_stmts(param_name, stmt.orelse, vul_lineno, file_path,
                                          repair_functions, controlled_params,
                                          visited_funcs, depth, tree, func_node)
                if result and result[0] in (1, 2, 3):
                    return result
            return None

        # 3. 立即检查约束（仅在 sink 在具体分支内时执行）
        for c in constraints:
            if c.var_name == param_name and c.op in ('==', '===', 'in', 'type_validated', 'regex_validated'):
                logger.info("[AST][Python] Branch constraint BLOCKS param {}: {} {}".format(param_name, c.op, c.value))
                return -1, None, 0

        # 4. 不等约束不阻断，继续回溯分支体
        result = _trace_in_stmts(param_name, body_stmts, vul_lineno, file_path,
                                repair_functions, controlled_params,
                                visited_funcs, depth, tree, func_node)
        # 在分支体内找到了明确的追踪结果，返回
        if result and result[0] in (1, 2, 4, 5):
            return result
        # 分支体内未找到赋值来源（code 3/-1），让外层 _trace_in_stmts 继续追踪更早语句
        return None

    # --- for 循环 ---
    elif isinstance(stmt, ast.For):
        # 检查循环变量
        target_name = _get_name(stmt.target)
        if target_name == param_name:
            return _trace_expr(param_name, stmt.iter, stmt.lineno, file_path,
                                repair_functions, controlled_params,
                                visited_funcs, depth, tree)
        # 在循环体内搜索
        result = _trace_in_stmts(param_name, stmt.body, vul_lineno, file_path,
                                  repair_functions, controlled_params,
                                  visited_funcs, depth, tree, func_node)
        if result and result[0] != -1:
            return result

    # --- match/case (Python 3.10+) ---
    if hasattr(ast, 'Match') and isinstance(stmt, ast.Match):
        subject_name = _get_name(stmt.subject)

        # 找到 sink 行号所在的 case
        target_case = None
        for case in stmt.cases:
            if case.body and int(case.body[0].lineno) <= vul_lineno <= int(case.body[-1].end_lineno):
                target_case = case
                break

        if target_case is not None:
            pattern = target_case.pattern

            # MatchValue(value=Constant(value=...)) — 固定值匹配
            if hasattr(ast, 'MatchValue') and isinstance(pattern, ast.MatchValue):
                if isinstance(pattern.value, ast.Constant) and subject_name == param_name:
                    logger.info("[AST][Python] match/case MatchValue BLOCKS param {}: {} == {}".format(
                        param_name, subject_name, pattern.value.value))
                    return -1, None, 0

            # MatchSingleton(value=True/False/None) — 类似 MatchValue
            elif hasattr(ast, 'MatchSingleton') and isinstance(pattern, ast.MatchSingleton):
                if subject_name == param_name:
                    logger.info("[AST][Python] match/case MatchSingleton BLOCKS param {}: {} == {}".format(
                        param_name, subject_name, pattern.value))
                    return -1, None, 0

            # MatchAs(pattern=None) — 通配符 _ → 不阻断
            elif hasattr(ast, 'MatchAs') and isinstance(pattern, ast.MatchAs) and pattern.pattern is None:
                pass

            # 其他 pattern 类型 → 不阻断
            else:
                pass

            # 继续在 case body 内回溯
            result = _trace_in_stmts(param_name, target_case.body, vul_lineno, file_path,
                                      repair_functions, controlled_params,
                                      visited_funcs, depth, tree, func_node)
            if result and result[0] in (1, 2, 4, 5):
                return result
            return None

        else:
            # sink 在 match 外或不在任何 case 中 → 遍历所有 case 的 body 搜索赋值
            for case in stmt.cases:
                result = _trace_in_stmts(param_name, case.body, vul_lineno, file_path,
                                          repair_functions, controlled_params,
                                          visited_funcs, depth, tree, func_node)
                if result and result[0] in (1, 2, 3):
                    return result
            return None

    # --- while 循环 ---
    elif isinstance(stmt, ast.While):
        # 1. 检查 sink 是否在 while 体内
        sink_in_body = (stmt.body and
                        int(stmt.body[0].lineno) <= vul_lineno <= int(stmt.body[-1].end_lineno))

        # 2. 如果 sink 在循环体内，提取 while 条件约束并检查等值约束
        if sink_in_body:
            constraints = extract_constraints_from_py_expr(stmt.test)
            for c in constraints:
                if c.var_name == param_name and c.op in ('==', '===', 'in', 'type_validated', 'regex_validated'):
                    logger.info("[AST][Python] While constraint BLOCKS param {}: {} {} {}".format(
                        param_name, c.var_name, c.op, c.value))
                    return -1, None, 0

        # 3. 继续在循环体内搜索
        result = _trace_in_stmts(param_name, stmt.body, vul_lineno, file_path,
                                  repair_functions, controlled_params,
                                  visited_funcs, depth, tree, func_node)
        if result and result[0] != -1:
            return result

    # --- try/except ---
    elif isinstance(stmt, ast.Try):
        for block in [stmt.body, stmt.handlers, stmt.orelse, stmt.finalbody]:
            if not block:
                continue
            if isinstance(block, list):
                # except handlers 是 ExceptHandler 对象列表
                if block and isinstance(block[0], ast.ExceptHandler):
                    for handler in block:
                        result = _trace_in_stmts(param_name, handler.body, vul_lineno,
                                                  file_path, repair_functions, controlled_params,
                                                  visited_funcs, depth, tree, func_node)
                        if result and result[0] != -1:
                            return result
                else:
                    result = _trace_in_stmts(param_name, block, vul_lineno, file_path,
                                              repair_functions, controlled_params,
                                              visited_funcs, depth, tree, func_node)
                    if result and result[0] != -1:
                        return result

    # --- return 语句 ---
    # return 语句不阻断追踪：变量出现在 return 中只是说明它被使用了，
    # 不影响在之前的赋值语句中找到它的来源
    # （不返回任何结果，让遍历继续到之前的赋值语句）

    return None


def _trace_expr(param_name, expr, lineno, file_path,
                 repair_functions, controlled_params,
                 visited_funcs, depth, tree):
    """追踪表达式的来源"""
    expr_str = _expr_to_str(expr)

    # 1. 检查是否是可控输入源
    if is_controllable(expr_str, controlled_params):
        logger.debug("[AST][Python] Found controllable source: {} at line {}".format(expr_str, lineno))
        return 1, expr_str, lineno

    # 2. 检查是否经过修复函数
    if is_repair(expr_str, repair_functions):
        logger.debug("[AST][Python] Found repair function: {} at line {}".format(expr_str, lineno))
        return 2, expr_str, lineno

    # 3. 如果表达式是函数调用，检查参数
    if isinstance(expr, ast.Call):
        call_name = _get_call_name(expr)
        # 检查调用参数中是否包含可控变量
        for arg in (expr.args or []):
            arg_str = _expr_to_str(arg)
            if is_controllable(arg_str, controlled_params):
                logger.debug("[AST][Python] Call {} with controllable arg: {}".format(call_name, arg_str))
                return 1, arg_str, lineno

            # 递归追踪参数
            arg_names = _collect_names(arg)
            for an in arg_names:
                result = parameters_back(an, [], lineno, file_path,
                                          repair_functions, controlled_params,
                                          visited_funcs, depth + 1)
                if result and result[0] in (1, 2):
                    return result

        # .format() 调用检查: "str".format(x) — x 可控则结果可控
        if isinstance(expr.func, ast.Attribute) and expr.func.attr == 'format':
            for arg in (expr.args or []):
                result = _trace_expr(param_name, arg, lineno, file_path,
                                      repair_functions, controlled_params,
                                      visited_funcs, depth, tree)
                if result and result[0] in (1, 2):
                    return result
            for kw in (expr.keywords or []):
                result = _trace_expr(param_name, kw.value, lineno, file_path,
                                      repair_functions, controlled_params,
                                      visited_funcs, depth, tree)
                if result and result[0] in (1, 2):
                    return result

        # 检查是否是修复函数调用
        if call_name and is_repair(call_name, repair_functions):
            return 2, call_name, lineno

        # 尝试进入函数定义追踪
        if call_name:
            func_def = _find_function_def(tree, call_name)
            if func_def and call_name not in visited_funcs:
                logger.debug("[AST][Python] Entering function {} for tracing".format(call_name))
                return _trace_function_return(func_def, expr, lineno, file_path,
                                               repair_functions, controlled_params,
                                               visited_funcs, depth, tree)

    # 4. 如果是二元运算，收集两边变量名并反向追踪
    if isinstance(expr, ast.BinOp):
        names = _collect_names(expr)
        for name in names:
            result = parameters_back(name, [], lineno, file_path,
                                      repair_functions, controlled_params,
                                      visited_funcs, depth + 1)
            if result and result[0] in (1, 2):
                return result
        # fallback: 递归检查子表达式
        result = _trace_expr(param_name, expr.left, lineno, file_path,
                              repair_functions, controlled_params,
                              visited_funcs, depth, tree)
        if result and result[0] in (1, 2):
            return result
        result = _trace_expr(param_name, expr.right, lineno, file_path,
                              repair_functions, controlled_params,
                              visited_funcs, depth, tree)
        if result and result[0] in (1, 2):
            return result

    # 5. f-string (JoinedStr)
    if isinstance(expr, ast.JoinedStr):
        for v in expr.values:
            if isinstance(v, ast.FormattedValue):
                result = _trace_expr(param_name, v.value, lineno, file_path,
                                      repair_functions, controlled_params,
                                      visited_funcs, depth, tree)
                if result and result[0] in (1, 2):
                    return result

    # 6. Subscript: x[0], x[key] — 追踪基础对象
    if isinstance(expr, ast.Subscript):
        result = _trace_expr(param_name, expr.value, lineno, file_path,
                              repair_functions, controlled_params,
                              visited_funcs, depth, tree)
        if result and result[0] in (1, 2):
            return result

    # 6.5 三元表达式 (IfExp): result if cond else other
    if isinstance(expr, ast.IfExp):
        true_names = set()
        false_names = set()
        _collect_names(expr.body, true_names, 0)
        _collect_names(expr.orelse, false_names, 0)
        constraints = extract_constraints_from_py_expr(expr.test)
        for c in constraints:
            if c.op in ('==', '===', 'in', 'type_validated', 'regex_validated'):
                if c.var_name in true_names and c.var_name not in false_names:
                    # 约束变量只在 true 分支 → true 路径中 var == fixed → 阻断
                    logger.info("[AST][Python] Ternary constraint BLOCKS: {} {} {}".format(c.var_name, c.op, c.value))
                    return -1, None, 0
                elif c.var_name in false_names and c.var_name not in true_names:
                    # 约束变量只在 false 分支 → false 路径中 var != fixed → 不阻断，追踪 false 分支
                    return _trace_expr(param_name, expr.orelse, lineno, file_path,
                                      repair_functions, controlled_params,
                                      visited_funcs, depth, tree)

    # 7. 如果表达式包含变量名，继续反向追踪这些变量
    names = _collect_names(expr)
    code4_candidates = []
    for name in names:
        result = parameters_back(name, [], lineno, file_path,
                                  repair_functions, controlled_params,
                                  visited_funcs, depth + 1)
        if result and result[0] in (1, 2):
            return result
        if result and result[0] == 4:
            code4_candidates.append(result)

    # code=4 候选排序：__init__ 优先级最低（需要类名匹配才能解析），
    # 普通函数优先级更高（有明确的调用者匹配）
    # 对每个候选尝试 _resolve_code4，返回第一个成功的
    if code4_candidates:
        code4_candidates.sort(key=lambda r: 1 if hasattr(r[1], 'name') and r[1].name == '__init__' else 0)
        # 先尝试 _resolve_code4 对每个候选
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                _src_lines = f.readlines()
        except Exception:
            _src_lines = []

        for c4_code, c4_cp in code4_candidates:
            r = _resolve_code4(c4_cp, tree, file_path,
                                [], controlled_params, repair_functions,
                                lineno, _src_lines, param_name)
            if r and r.get('code') in (1, 2):
                return r['code'], r.get('source', param_name)
        # 所有候选的 _resolve_code4 都失败，返回第一个（让 scan_parser 的 _resolve_code4 继续尝试）
        return code4_candidates[0]

    return 3, None, 0


def _find_function_def(tree, func_name):
    """在 AST 树中查找函数定义"""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == func_name:
                return node
    return None


def _judge_from_summary_py(summary, call_node, controlled_params):
    """根据函数摘要判定返回值可控性（Python版）

    返回: (code, source, lineno) 三元组或 None（摘要无法判定，走原路径）
    """
    if controlled_params is None:
        return None

    call_args = call_node.args or []

    for rf in summary.return_flow:
        if rf.origin_type == "param":
            for param_idx in rf.dep_params:
                if param_idx < len(call_args):
                    arg_str = _expr_to_str(call_args[param_idx])
                    if is_controllable(arg_str, controlled_params):
                        return (1, arg_str, getattr(call_node, 'lineno', 0))
                    names = _collect_names(call_args[param_idx])
                    if names:
                        return ('deps', list(names), getattr(call_node, 'lineno', 0))

        elif rf.origin_type == "call":
            if is_controllable(rf.origin, controlled_params):
                return (1, rf.origin, getattr(call_node, 'lineno', 0))
            knowledge = lookup_builtin(rf.origin)
            if knowledge and (knowledge.get("passthrough") or knowledge.get("param_flow")):
                for param_idx in rf.dep_params:
                    if param_idx < len(call_args):
                        arg_str = _expr_to_str(call_args[param_idx])
                        if is_controllable(arg_str, controlled_params):
                            return (1, arg_str, getattr(call_node, 'lineno', 0))
            for param_idx in rf.dep_params:
                if param_idx < len(call_args):
                    names = _collect_names(call_args[param_idx])
                    if names:
                        return ('deps', list(names), getattr(call_node, 'lineno', 0))

        elif rf.origin_type == "global":
            if is_controllable(rf.origin, controlled_params):
                return (1, rf.origin, getattr(call_node, 'lineno', 0))

        elif rf.origin_type == "literal":
            continue

    return None


def _trace_function_return(func_def, call_node, lineno, file_path,
                            repair_functions, controlled_params,
                            visited_funcs, depth, tree):
    """追踪函数的返回值是否可控
    
    核心原则：函数体是封闭作用域，只通过形参→实参映射判断可控性。
    不在函数体内再调 parameters_back（避免和调用者的赋值行冲突导致循环）。
    返回值:
        (1, source) — 返回值可控，依赖的实参来源
        (2, func_name) — 返回值经过修复函数处理
        (3, None) — 未确认
        (-1, None) — 不可控
        也可以返回 ('deps', [var1, var2, ...]) 表示返回值依赖这些调用者变量，
        由上层 _trace_stmt / _trace_in_stmts 继续向上追踪。
    """
    func_name = func_def.name

    # 查内置知识库（优先级高于函数体分析）
    call_func_name = None
    if hasattr(call_node.func, 'id'):
        call_func_name = call_node.func.id
    elif hasattr(call_node.func, 'attr'):
        call_func_name = call_node.func.attr
        # 补全模块前缀，如 os.path.join
        if hasattr(call_node.func, 'value'):
            val = call_node.func.value
            if hasattr(val, 'id'):
                call_func_name = val.id + '.' + call_func_name
            elif hasattr(val, 'attr'):
                call_func_name = val.attr + '.' + call_func_name

    if call_func_name:
        knowledge = lookup_builtin(call_func_name)
        if knowledge:
            if knowledge["safe"] and not knowledge["passthrough"] and not knowledge.get("param_flow"):
                return -1, None, 0
            if knowledge["passthrough"] or knowledge.get("param_flow"):
                deps = set()
                for arg_idx in knowledge["passthrough"]:
                    if arg_idx < len(call_node.args or []):
                        arg_names = _collect_names(call_node.args[arg_idx])
                        deps.update(arg_names)
                if deps:
                    return ('deps', list(deps), getattr(call_node, 'lineno', lineno))
            return -1, None, 0  # 不透传 → 安全

    # 1.5. 查函数摘要
    callee_summary = lookup_summary(func_name)
    if callee_summary and callee_summary.return_flow:
        result = _judge_from_summary_py(callee_summary, call_node, controlled_params)
        if result:
            return result

    # 建立参数映射：调用实参 → 函数形参
    arg_map = {}
    func_args = func_def.args.args
    call_args = call_node.args or []

    # Source Discovery check: user-defined source producer (before param loop)
    _is_source_producer = False
    if _source_registry is not None:
        source_info = _source_registry.is_source_producer(func_name)
        if source_info:
            _is_source_producer = True
            logger.debug('[AST][Python] Source Discovery: {} is a source producer ({})'.format(
                func_name, source_info.origin))

    # 收集哪些形参对应的实参是可控的
    # 注意：这里只用 is_controllable 直接检查，不调 parameters_back
    # 因为 parameters_back 从 lineno 开始追踪会和当前赋值行冲突
    controllable_param_names = set()
    caller_var_names = set()  # 实参中引用的变量名，需要上层继续追踪
    for i, param in enumerate(func_args):
        if i < len(call_args):
            arg_str = _expr_to_str(call_args[i])
            arg_map[param.arg] = arg_str
            if _is_source_producer:
                # source producer → 所有形参都被视为可控
                controllable_param_names.add(param.arg)
            if is_controllable(arg_str, controlled_params):
                controllable_param_names.add(param.arg)
            else:
                # 收集实参中的变量名，但不立即追踪
                for an in _collect_names(call_args[i]):
                    caller_var_names.add(an)

    # 在函数体内做赋值链传播：如果赋值右边包含可控形参，左边也标记可控
    controllable_local = set(controllable_param_names)
    for _ in range(3):  # 迭代传播
        for stmt in func_def.body:
            if isinstance(stmt, ast.Assign) and stmt.value:
                for target in stmt.targets:
                    tname = _get_name(target)
                    if tname and tname not in controllable_local:
                        rhs_names = _collect_names(stmt.value)
                        if rhs_names & controllable_local:
                            controllable_local.add(tname)

    # 在函数体中查找 return 语句
    # Source Discovery: 如果函数本身是 source producer，返回值直接可控
    if _is_source_producer:
        for node in ast.walk(func_def):
            if isinstance(node, ast.Return) and node.value:
                return_str = _expr_to_str(node.value)
                logger.debug("[AST][Python] Source producer {} returns: {}".format(func_name, return_str))
                return 1, return_str, lineno
        # 无 return 语句但仍是 source producer → 仍然视为可控
        return 1, func_name, lineno

    for node in ast.walk(func_def):
        if isinstance(node, ast.Return) and node.value:
            # 先检查返回值表达式本身是否是可控源
            return_str = _expr_to_str(node.value)
            if is_controllable(return_str, controlled_params):
                logger.debug("[AST][Python] Function {} returns controllable source directly: {}".format(
                    func_name, return_str))
                return 1, return_str, lineno

            # 检查返回值中引用的变量是否在可控局部变量集合中
            return_names = _collect_names(node.value)

            # 检查返回值是否包含可控局部变量（赋值链传播结果）
            matched = return_names & controllable_local
            if matched:
                # 可控局部变量最终来自形参 → 形参来自调用处的实参
                # 收集这些实参中的变量名，返回给上层继续追踪
                deps = set()
                for var_name in matched:
                    if var_name in arg_map:
                        # 形参直接出现在返回值中 → 取对应实参的变量名
                        arg_str = arg_map[var_name]
                        if is_controllable(arg_str, controlled_params):
                            return 1, arg_str, lineno
                        deps.update(_collect_names_from_str(arg_str))
                    else:
                        # 局部变量间接传播 → 其来源仍可追溯到形参
                        deps.update(_collect_names(node.value))
                if deps:
                    logger.debug("[AST][Python] Function {} return depends on caller vars: {}".format(
                        func_name, deps))
                    return 'deps', list(deps), lineno

            # fallback: 文本匹配形参名出现在返回值中
            return_str = _expr_to_str(node.value)
            for param_name, arg_str in arg_map.items():
                if is_controllable(arg_str, controlled_params):
                    if param_name in return_str or _contains_name(node.value, param_name):
                        logger.debug("[AST][Python] Function {} returns controllable param {} (text match)".format(
                            func_name, param_name))
                        return 1, arg_str, lineno

    # 返回值没有明确的可控来源，但有未确认的调用者变量
    # 把 caller_var_names 交给上层继续追踪
    if caller_var_names:
        logger.debug("[AST][Python] Function {} return may depend on caller vars: {}".format(
            func_name, caller_var_names))
        return 'deps', list(caller_var_names), 0

    return 3, None, 0


# ---------------------------------------------------------------------------
# 入口函数
# ---------------------------------------------------------------------------

def _resolve_code4(func_def, tree, file_path, sensitive_func,
                    controlled_params, repair_functions,
                    target_line, source_lines, arg_str, depth=0):
    """递归解析 code=4: 函数参数追踪调用者链

    处理:
    - __init__ → ClassName(...) 构造调用
    - __call__ → instance(...) 实例调用
    - 普通方法 → obj.method(...) / func(...)
    - 递归: 调用者参数也是 code=4 时继续向上追踪
    """
    if depth > 3 or not isinstance(func_def, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None

    source_ln = target_line
    chain = ["{}:{}".format(source_ln, source_lines[source_ln - 1].strip()
                            if source_ln <= len(source_lines) else arg_str)]

    # ---- 检查函数体内是否有敏感调用（直接或间接） ----
    has_sink = _func_has_sink(func_def, sensitive_func)

    # ---- 确定要匹配的调用名 ----
    call_names_to_match = []
    parent_class = _find_class_containing_method(tree, func_def)

    if func_def.name == '__init__':
        if parent_class:
            call_names_to_match = [parent_class.name]
            # 也匹配所有继承该类的子类的构造调用
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node is not parent_class:
                    for base in node.bases:
                        base_name = _get_name(base)
                        if base_name == parent_class.name:
                            call_names_to_match.append(node.name)
                            break
    elif func_def.name == '__call__':
        # __call__: 匹配 instance(args) 形式
        # 需要找到所有 ClassName(...) 调用，然后追踪变量是否是 ClassName 实例
        if parent_class:
            call_names_to_match = [parent_class.name, func_def.name]
    else:
        call_names_to_match = [func_def.name]

    if not has_sink and not call_names_to_match:
        return None

    # ---- 在整个文件中查找谁调用了这个函数 ----
    # 收集所有文件的 AST（跨文件追踪）
    all_trees = [(tree, file_path)]
    pt = globals().get('_ast_object_singleton')
    if pt and hasattr(pt, 'pre_result'):
        for other_fp, other_data in pt.pre_result.items():
            if other_fp != file_path and 'ast_nodes' in other_data:
                all_trees.append((other_data['ast_nodes'], other_fp))
    for src_tree, src_fp in all_trees:
      for caller_node in ast.walk(src_tree):
        if not isinstance(caller_node, ast.Call):
            continue
        cn = _get_call_name(caller_node)

        matched = False
        for match_name in call_names_to_match:
            if cn and (cn == match_name or cn.endswith('.' + match_name)):
                matched = True
                break

        # __call__ 特殊处理: 任何变量名() 调用都可能是 __call__
        if not matched and func_def.name == '__call__' and parent_class:
            if cn and '.' not in cn:
                var_type = _resolve_variable_type(src_tree, cn, caller_node.lineno, {})
                if var_type == parent_class.name:
                    matched = True

        if not matched or not hasattr(caller_node, 'lineno'):
            continue

        # 找到调用点，检查实参
        found = False
        for caller_arg in (caller_node.args or []):
            ca_str = _expr_to_str(caller_arg)
            if is_controllable(ca_str, controlled_params):
                return {"code": 1, "chain": chain, "source": ca_str}

            # 反向追踪实参中的变量
            ca_names = _collect_names(caller_arg)
            for can in ca_names:
                ccode, ccp = parameters_back(can, [], caller_node.lineno, src_fp,
                                              repair_functions, controlled_params)
                if ccode == 1:
                    return {"code": 1, "chain": chain, "source": ccp}

                # 递归: 调用者参数也是函数参数(code=4)，继续向上追踪
                if ccode == 4 and isinstance(ccp, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # 递归时用调用者所在文件的 tree
                    caller_tree = None
                    if src_fp == file_path:
                        caller_tree = tree
                    else:
                        pt_obj = globals().get('_ast_object_singleton')
                        if pt_obj and hasattr(pt_obj, 'pre_result') and src_fp in pt_obj.pre_result:
                            caller_tree = pt_obj.pre_result[src_fp].get('ast_nodes')
                    result = _resolve_code4(ccp, caller_tree, src_fp, sensitive_func,
                                            controlled_params, repair_functions,
                                            target_line, source_lines, arg_str, depth + 1)
                    if result and result.get('code') == 1:
                        return result

            found = True  # 标记已处理过有参数的调用点
            break  # 只处理第一个参数
        if found:
            break  # 只处理第一个有参数的调用点

    return None


def _func_has_sink(func_def, sensitive_func):
    """检查函数体内是否包含敏感调用（直接或间接通过 self.xxx()）"""
    for inner_node in ast.walk(func_def):
        if isinstance(inner_node, ast.Call):
            inner_name = _get_call_name(inner_node)
            if inner_name:
                for sf in sensitive_func:
                    if inner_name == sf or inner_name.endswith('.' + sf):
                        return True
    return False


def _init_function_summaries(file_path):
    """初始化 Python 文件的函数摘要"""
    global _summaries_initialized, _file_summaries

    if _summaries_initialized:
        return

    try:
        from core.core_engine.function_summary import SummaryCacheManager
        from core.core_engine.python.summary_generator import generate_file_summaries, generate_summaries_for_target

        target_dir = file_path
        pt = _ast_object_singleton
        if pt and hasattr(pt, 'target_directory'):
            target_dir = pt.target_directory
        elif pt and hasattr(pt, 'pre_result'):
            paths = list(pt.pre_result.keys())
            if len(paths) > 1:
                import os
                target_dir = os.path.commonpath(paths)
            elif paths:
                import os
                target_dir = os.path.dirname(paths[0])

        cache_mgr = SummaryCacheManager()

        files_dict = {}
        if pt and hasattr(pt, 'pre_result'):
            for fp, data in pt.pre_result.items():
                if data.get('language') == 'python':
                    try:
                        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                            files_dict[fp] = f.read()
                    except:
                        pass
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                files_dict[file_path] = f.read()
        except:
            pass

        if files_dict:
            cached = cache_mgr.load_or_generate(target_dir, files_dict)
            need_generate = {fp: content for fp, content in files_dict.items()
                             if not cached.get(fp) or not cached[fp].functions}
            if need_generate:
                new_summaries = generate_summaries_for_target(target_dir, need_generate)
                for fp, fs in new_summaries.items():
                    cached[fp] = fs
                    cache_mgr.save_file_summary(target_dir, fp, fs)
            _file_summaries = cached
            logger.debug(f"[AST][Python] 摘要初始化完成: {len(_file_summaries)} 个文件")

        _summaries_initialized = True
    except Exception as e:
        logger.debug(f"[AST][Python] 摘要初始化失败: {e}")
        _summaries_initialized = True


def find_sinks(sink_names, files):
    """
    AST-based sink 查找。遍历所有文件的 AST 节点，查找匹配的函数调用。
    支持直接调用匹配和间接调用检测。

    :param sink_names: list of SinkName(class_, method) from parse_sink_names()
    :param files: 文件路径列表
    :return: list of dict, 每项包含:
        - 'file_path': 文件路径
        - 'lineno': 行号
        - 'node': AST 调用节点
        - 'is_indirect': bool, 是否为间接调用
        - 'callee_name': str, 被调用函数名
        - 'class_name': str or None, 类名/对象名
        - 'matched_sink': SinkName or None
    """
    from core.utils import SinkName

    results = []

    for file_path in files:
        file_path = _ast_object_singleton.get_path(file_path)
        if not file_path:
            continue
        tree = _ast_object_singleton.get_nodes(file_path)
        if not tree or not hasattr(tree, 'body'):
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            call_name = _get_call_name(node)
            func = node.func

            # 间接调用检测：func 是 Name 且不是直接匹配的 sink
            # 如 func_var = os.system; func_var(x)
            is_indirect = False
            if isinstance(func, ast.Name):
                # 检查是否所有 sink 都不匹配这个简单名称
                if not any(s.class_ is None and s.method == func.id for s in sink_names):
                    # 如果 func.id 不匹配任何 sink 的 method，可能是间接调用
                    # 但也可能是普通函数调用，只在 node.func 不是已知 sink 时标记
                    is_indirect = False
            elif isinstance(func, ast.Attribute):
                pass
            else:
                # ast.Subscript 等其他类型 → 间接调用
                # 如 globals()['os.system'](x)
                is_indirect = True

            if is_indirect:
                for sink in sink_names:
                    results.append({
                        'file_path': file_path,
                        'lineno': node.lineno if hasattr(node, 'lineno') else 0,
                        'node': node,
                        'is_indirect': True,
                        'callee_name': '<indirect>',
                        'class_name': None,
                        'matched_sink': sink,
                    })
                    break
                continue

            if not call_name:
                continue

            for sink in sink_names:
                if sink.class_ is None:
                    # 模糊匹配：call_name == method 或 call_name 以 .method 结尾
                    if call_name == sink.method or call_name.endswith('.' + sink.method):
                        results.append({
                            'file_path': file_path,
                            'lineno': node.lineno if hasattr(node, 'lineno') else 0,
                            'node': node,
                            'is_indirect': False,
                            'callee_name': call_name,
                            'class_name': call_name.rsplit('.', 1)[0] if '.' in call_name else None,
                            'matched_sink': sink,
                        })
                        break
                else:
                    # 精确匹配：call_name 应该是 class_.method
                    if call_name == '{}.{}'.format(sink.class_, sink.method):
                        results.append({
                            'file_path': file_path,
                            'lineno': node.lineno if hasattr(node, 'lineno') else 0,
                            'node': node,
                            'is_indirect': False,
                            'callee_name': call_name,
                            'class_name': sink.class_,
                            'matched_sink': sink,
                        })
                        break

    return results


def scan_parser(sensitive_func, vul_lineno, file_path, repair_functions=[], controlled_params=[], svid=None):
    """
    Python AST scan parser - 分析敏感函数参数是否可控

    :param sensitive_func: 要检测的敏感函数列表，如 ["os.system", "eval"]
    :param vul_lineno: 漏洞函数所在行号
    :param file_path: 文件路径
    :param repair_functions: 修复函数列表
    :param controlled_params: 可控参数列表
    :param svid: 规则 ID
    :return: scan_results 列表，每个元素是 {"code": N, "chain": [...], "source": ...}
    """
    global scan_results, is_repair_functions, is_controlled_params, scan_chain, _trace_visited
    global _summaries_initialized

    # 清空追踪去重集合和缓存
    _trace_visited = set()
    _trace_cache.clear()
    _summaries_initialized = False
    _init_function_summaries(file_path)

    # Initialize Source Discovery (once per project)
    global _source_registry

    try:
        scan_chain = ["start"]
        scan_results = []
        is_repair_functions = repair_functions
        is_controlled_params = controlled_params

        if _ast_object_singleton is None:
            logger.debug("[AST][Python] ast_object is None, skip")
            return scan_results

        tree = _ast_object_singleton.get_nodes(file_path)
        if not tree or not hasattr(tree, 'body'):
            logger.debug("[AST][Python] No AST nodes for {}".format(file_path))
            return scan_results

        # Initialize Source Discovery (once per project, after tree is available)
        if _source_registry is None:
            project_dir = os.path.dirname(os.path.abspath(file_path))
            try:
                _source_registry = discover_sources(project_dir, tree, file_path)
                # Inject discovered source members into controlled_params
                if _source_registry.source_members:
                    extra_sources = _source_registry.get_all_source_names()
                    controlled_params = list(controlled_params) + extra_sources
                    is_controlled_params = controlled_params
                    logger.debug('[AST][Python] Source Discovery injected {} source members'.format(len(extra_sources)))
            except Exception as e:
                logger.debug('[AST][Python] Source Discovery init error: {}'.format(e))

        target_line = int(vul_lineno)

        # 解析 import 语句，用于跨文件追踪
        import_map = _parse_imports(tree, file_path)

        # 读取源码行用于日志
        source_lines = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                source_lines = f.readlines()
        except Exception:
            pass

        # 在 AST 中查找在目标行调用了敏感函数的节点
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            call_name = _get_call_name(node)
            if not call_name:
                continue

            # 检查是否匹配敏感函数（支持 module.func 和纯 func 匹配）
            matched = False
            for sf in sensitive_func:
                if call_name == sf or call_name.endswith('.' + sf):
                    matched = True
                    break
            if not matched:
                continue

            # 检查行号
            if not hasattr(node, 'lineno') or node.lineno != target_line:
                continue

            logger.debug("[AST][Python] Found sensitive call: {}() at line {}".format(call_name, target_line))

            # ---- 赋值链迭代传播 ----
            # 找到目标行所在的函数，在函数内做变量传播：
            # 如果 x = tainted_var，则 x 也标记为可控
            func_node = _find_function_at_line(tree, target_line)
            extra_controlled = set()
            if func_node:
                # 收集函数体内所有赋值关系: {lhs: set_of_rhs_names}
                assign_map = {}
                for s in ast.walk(func_node):
                    if isinstance(s, ast.Assign) and s.value:
                        for t in s.targets:
                            tname = _get_name(t)
                            if tname:
                                assign_map[tname] = _collect_names(s.value)

                # 第一轮：用 parameters_back 标记 rhs 中可控的变量
                for lhs_name, rhs_names in assign_map.items():
                    for rn in rhs_names:
                        code, _, _ = parameters_back(rn, [], target_line, file_path,
                                                   repair_functions, controlled_params)
                        if code == 1:
                            extra_controlled.add(lhs_name)
                            break

                # 后续迭代传播：如果 rhs 包含已传播变量，lhs 也标记
                changed = True
                iterations = 0
                while changed and iterations < 5:
                    changed = False
                    iterations += 1
                    for lhs_name, rhs_names in assign_map.items():
                        if lhs_name in extra_controlled:
                            continue
                        if rhs_names & extra_controlled:
                            extra_controlled.add(lhs_name)
                            changed = True

            extended_controlled = list(controlled_params) + list(extra_controlled)

            # 分析每个参数
            for arg in (node.args or []):
                arg_str = _expr_to_str(arg)

                # 直接检查参数是否是可控源（含传播后的变量）
                if is_controllable(arg_str, extended_controlled):
                    source_ln = target_line
                    chain = ["{}:{}".format(source_ln, source_lines[source_ln - 1].strip() if source_ln <= len(source_lines) else arg_str)]
                    scan_results.append({"code": 1, "chain": chain, "source": arg_str})
                    break

                # 如果参数是函数调用，直接走 _trace_expr 追踪（Source Discovery 支持）
                if isinstance(arg, ast.Call):
                    call_name = _get_call_name(arg)
                    func_def = _find_function_def(tree, call_name) if call_name else None
                    if func_def:
                        result = _trace_function_return(func_def, arg, target_line, file_path,
                                                     repair_functions, extended_controlled,
                                                     set(), 0, tree)
                        if result and result[0] == 1:
                            source_ln = result[2] if result[2] else target_line
                            chain = ["{}:{}".format(source_ln, source_lines[source_ln - 1].strip() if source_ln <= len(source_lines) else arg_str)]
                            scan_results.append({"code": 1, "chain": chain, "source": result[1]})
                            break
                        elif result and result[0] == 2:
                            source_ln = result[2] if result[2] else target_line
                            chain = ["{}:{}".format(source_ln, source_lines[source_ln - 1].strip() if source_ln <= len(source_lines) else arg_str)]
                            scan_results.append({"code": 2, "chain": chain, "source": result[1]})
                            break

                # 收集参数中的变量名，反向追踪
                arg_names = _collect_names(arg)
                # 收集所有追踪结果，排序后优先处理有 sink 的函数
                traced_results = []
                for an in arg_names:
                    code, cp, src_ln = parameters_back(an, [], target_line, file_path,
                                                repair_functions, extended_controlled)
                    traced_results.append((code, cp, an, src_ln))
                
                # 排序：code=1/2 优先，code=4 中 __init__ 最低
                def _sort_key(item):
                    c, cp, _, _ = item
                    if c in (1, 2): return (0, 0)
                    if c == 4:
                        fn = getattr(cp, 'name', '') if cp else ''
                        return (1, 1 if fn == '__init__' else 0)
                    return (2, 0)
                traced_results.sort(key=_sort_key)
                
                for code, cp, an, src_ln in traced_results:
                    source_ln = src_ln if src_ln else target_line
                    chain = ["{}:{}".format(source_ln, source_lines[source_ln - 1].strip() if source_ln <= len(source_lines) else arg_str)]

                    if code == 1:
                        scan_results.append({"code": 1, "chain": chain, "source": cp})
                        break
                    elif code == 2:
                        scan_results.append({"code": 2, "chain": chain, "source": cp})
                        break
                    elif code == 4:
                        # code=4: 变量是函数参数，需要继续追踪
                        result = _resolve_code4(cp, tree, file_path, sensitive_func,
                                                extended_controlled, repair_functions,
                                                target_line, source_lines, arg_str)
                        if result and result.get('code') in (1, 2):
                            # 找到可控路径，替换之前的 fallback
                            scan_results = [result]
                            break
                        # 如果候选不是 __init__，也尝试 self.xxx 的 __init__ 路径
                        # 因为 _trace_expr 排序时普通函数优先于 __init__
                        if hasattr(cp, 'name') and cp.name != '__init__':
                            for other_an in arg_names:
                                if other_an.startswith('self.') and other_an != an:
                                    init_code, init_cp = parameters_back(other_an, [], target_line, file_path,
                                                                          repair_functions, extended_controlled)
                                    if init_code == 4 and hasattr(init_cp, 'name') and init_cp.name == '__init__':
                                        init_result = _resolve_code4(init_cp, tree, file_path, sensitive_func,
                                                                      extended_controlled, repair_functions,
                                                                      target_line, source_lines, arg_str)
                                        if init_result and init_result.get('code') in (1, 2):
                                            scan_results = [init_result]
                                            break
                            if scan_results and any(r.get('code') in (1, 2) for r in scan_results):
                                break
                        # 如果还没找到更好的结果，保存 code=4 作为 fallback
                        if not any(r.get('code') in (1, 2) for r in scan_results):
                            scan_results = [{"code": 4, "chain": chain, "source": arg_str}]
                        # 继续处理下一个参数
                    elif code == 3:
                        scan_results.append({"code": 3, "chain": chain, "source": cp})
                    elif code == -1:
                        # 分支约束阻断：参数不可控
                        scan_results.append({"code": -1, "chain": chain, "source": cp})
                        break
                else:
                    continue
                break

            if not scan_results:
                # 没有在当前文件找到敏感调用，尝试跨文件追踪
                # 检查目标行调用的函数是否是从其他文件 import 的
                cross_file_result = _try_cross_file_trace(
                    tree, target_line, sensitive_func, file_path,
                    repair_functions, controlled_params, import_map, source_lines)
                if cross_file_result:
                    scan_results = cross_file_result
                else:
                    # 最终 fallback
                    source_ln = target_line
                    chain = ["{}:{}".format(source_ln, source_lines[source_ln - 1].strip() if source_ln <= len(source_lines) else call_name)]
                    scan_results.append({"code": -1, "chain": chain, "source": None})

            # 只处理第一个匹配的调用
            break

        # 如果主循环没有匹配到任何敏感函数调用，尝试跨文件追踪
        if not scan_results and import_map:
            cross_file_result = _try_cross_file_trace(
                tree, target_line, sensitive_func, file_path,
                repair_functions, controlled_params, import_map, source_lines)
            if cross_file_result:
                scan_results = cross_file_result

    except Exception:
        logger.warning("[AST][Python] scan_parser error: {}".format(traceback.format_exc()))

    return scan_results


def _try_cross_file_trace(tree, target_line, sensitive_func, file_path,
                           repair_functions, controlled_params, import_map, source_lines):
    """跨文件追踪：检查目标行调用的 import 函数内部是否包含敏感调用"""
    
    # 找到目标行的所有调用
    target_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and hasattr(node, 'lineno') and node.lineno == target_line:
            call_name = _get_call_name(node)
            if call_name:
                target_calls.append((call_name, node))
    
    if not target_calls:
        return None
    
    for call_name, call_node in target_calls:
        # 提取被调用的函数名（去掉对象前缀）
        func_name = call_name.split('.')[-1] if '.' in call_name else call_name
        
        # 尝试多种匹配策略：
        # 1. 函数名直接在 import_map 中（如 run_command）
        # 2. 对象的类名在 import_map 中（如 Executor → ex.run()）
        # 3. 完整调用名在 import_map 中
        imported_path = None
        imported_func_name = func_name
        is_class_method = False
        
        if func_name in import_map:
            imported_path = import_map[func_name]
        elif '.' in call_name:
            # ex.run() → obj_name='ex', 尝试从 import_map 找 ex 对应的类
            # 也尝试直接匹配完整名
            if call_name in import_map:
                imported_path = import_map[call_name]
            else:
                # 尝试从当前 AST 中找到 ex 的类型
                obj_name = call_name.split('.')[0]
                obj_type = _resolve_variable_type(tree, obj_name, target_line, import_map)
                if obj_type and obj_type in import_map:
                    imported_path = import_map[obj_type]
                    is_class_method = True
        
        if not imported_path:
            continue
        
        # 加载被 import 文件的 AST
        imported_tree = None
        try:
            if _ast_object_singleton:
                imported_tree = _ast_object_singleton.get_nodes(imported_path)
            if not imported_tree:
                with open(imported_path, 'r', encoding='utf-8', errors='replace') as f:
                    imported_tree = ast.parse(f.read(), filename=imported_path)
        except Exception:
            continue
        
        if not imported_tree:
            continue
        
        # 在被 import 文件中找到函数定义
        func_def = _find_function_def(imported_tree, imported_func_name)
        if not func_def and is_class_method:
            # 类方法：在类中查找方法
            for cls_node in ast.walk(imported_tree):
                if isinstance(cls_node, ast.ClassDef):
                    for item in cls_node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == func_name:
                            func_def = item
                            break
                    if func_def:
                        break
        if not func_def:
            continue
        
        # 检查函数内部是否调用了敏感函数
        for inner_node in ast.walk(func_def):
            if not isinstance(inner_node, ast.Call):
                continue
            inner_name = _get_call_name(inner_node)
            if not inner_name:
                continue
            
            # 检查是否匹配内置敏感函数 + 规则配置的函数
            is_sink = False
            for sf in BUILTIN_SENSITIVE_SINKS + list(sensitive_func):
                if inner_name == sf or inner_name.endswith('.' + sf):
                    is_sink = True
                    break
            if not is_sink:
                continue
            
            # 找到了间接 sink！
            # 检查当前调用点的实参是否可控
            for arg in (call_node.args or []):
                arg_str = _expr_to_str(arg)
                
                # 直接检查可控性
                if is_controllable(arg_str, controlled_params):
                    chain = ["{}:{}".format(
                        target_line,
                        source_lines[target_line - 1].strip() if target_line <= len(source_lines) else call_name)]
                    return [{"code": 1, "chain": chain, "source": arg_str}]
                
                # 反向追踪
                arg_names = _collect_names(arg)
                for an in arg_names:
                    code, cp, src_ln = parameters_back(an, [], target_line, file_path,
                                                repair_functions, controlled_params)
                    if code == 1:
                        source_ln = src_ln if src_ln else target_line
                        chain = ["{}:{}".format(
                            source_ln,
                            source_lines[source_ln - 1].strip() if source_ln <= len(source_lines) else call_name)]
                        return [{"code": 1, "chain": chain, "source": cp}]

            # 直接参数不可控，如果是类方法，检查 self.xxx 属性来源
            # 通过 __init__ 追踪构造函数参数
            if is_class_method:
                self_result = _trace_cross_file_self_attribute(
                    imported_tree, func_def, tree, call_node, target_line,
                    file_path, repair_functions, controlled_params, source_lines)
                if self_result:
                    return self_result
        
        # 没有找到间接 sink，检查是否需要返回不可控
        chain = ["{}:{}".format(
            target_line,
            source_lines[target_line - 1].strip() if target_line <= len(source_lines) else call_name)]
        return [{"code": -1, "chain": chain, "source": None}]
    
    return None


def _trace_cross_file_self_attribute(imported_tree, method_def, caller_tree,
                                      call_node, target_line, file_path,
                                      repair_functions, controlled_params,
                                      source_lines):
    """跨文件 self.xxx 属性追踪
    
    当 ex.run('ls') 中 'ls' 不可控时，检查方法体内是否通过 self.xxx 
    使用了构造函数参数。完整链路：
    
    ex = Executor(user_input)          ← caller_tree 中
         ↓ __init__(self, base)        ← imported_tree 中
         ↓ self.base = base
    ex.run('ls')                       ← call_node
         ↓ os.popen(self.base + arg)   ← method_def 中
         ↑ self.base 可控因为 __init__ 参数 base 来自 user_input
    
    :return: [{"code": 1, ...}] or None
    """
    # 1. 找到方法所属的类
    class_node = None
    for node in ast.walk(imported_tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if item is method_def:
                    class_node = node
                    break
            if class_node:
                break
    
    if not class_node:
        return None
    
    # 2. 收集方法体内使用的 self.xxx 属性名
    #    通过 _collect_names 收集所有 self.xxx，然后筛选 self. 前缀的
    used_self_attrs = set()
    for inner in ast.walk(method_def):
        if isinstance(inner, ast.Attribute) and isinstance(inner.value, ast.Name) and inner.value.id == 'self':
            used_self_attrs.add('self.' + inner.attr)
    
    if not used_self_attrs:
        return None
    
    # 3. 在 __init__ 中建立 self.xxx → __init__参数名 的映射
    init_method = None
    for item in class_node.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == '__init__':
            init_method = item
            break
    
    if not init_method:
        return None
    
    # self.attr → init_param_name 映射
    self_attr_to_param = {}
    for stmt in init_method.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                target_name = _get_name(target)
                if target_name and target_name in used_self_attrs:
                    # self.base = base → {'self.base': 'base'}
                    rhs_name = _get_name(stmt.value)
                    if rhs_name:
                        # 验证 rhs_name 确实是 __init__ 参数
                        for arg in init_method.args.args:
                            if arg.arg == rhs_name and arg.arg != 'self':
                                self_attr_to_param[target_name] = rhs_name
    
    if not self_attr_to_param:
        return None
    
    # 4. 找到构造函数调用处：ex = Executor(...)
    #    从 caller_tree 中查找 ClassName(...) 的调用
    class_name = class_node.name
    constructor_calls = []
    for node in ast.walk(caller_tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == class_name:
                constructor_calls.append(node)
            elif isinstance(node.func, ast.Attribute) and node.func.attr == class_name:
                constructor_calls.append(node)
    
    # 5. 对每个构造调用，检查构造参数是否可控
    for ctor_call in constructor_calls:
        # 建立 构造参数位置 → 参数名 的映射
        init_params = [a for a in init_method.args.args if a.arg != 'self']
        
        for i, ctor_arg in enumerate(ctor_call.args or []):
            # 找到这个位置对应的 __init__ 参数名
            param_name = init_params[i].arg if i < len(init_params) else None
            if not param_name:
                continue
            
            # 检查这个参数是否被 self.xxx 使用
            if param_name not in self_attr_to_param.values():
                continue
            
            # 检查构造调用的实参是否可控
            arg_str = _expr_to_str(ctor_arg)
            if is_controllable(arg_str, controlled_params):
                chain = ["{}:{}".format(
                    target_line,
                    source_lines[target_line - 1].strip() if target_line <= len(source_lines) else _get_call_name(call_node))]
                return [{"code": 1, "chain": chain, "source": arg_str}]
            
            # 反向追踪构造参数
            arg_names = _collect_names(ctor_arg)
            for an in arg_names:
                code, cp, src_ln = parameters_back(an, [], ctor_call.lineno if hasattr(ctor_call, 'lineno') else target_line,
                                            file_path, repair_functions, controlled_params)
                if code == 1:
                    source_ln = src_ln if src_ln else target_line
                    chain = ["{}:{}".format(
                        source_ln,
                        source_lines[source_ln - 1].strip() if source_ln <= len(source_lines) else _get_call_name(call_node))]
                    return [{"code": 1, "chain": chain, "source": cp}]
    
    return None


def analysis_params(param, expr_lineno, vul_function, line, file_path,
                     repair_functions, controlled_params, isexternal=True):
    """
    分析参数可控性（供 CAST.is_controllable_param 调用）

    :param param: 变量名字符串
    :param expr_lineno: 表达式行号列表（Python 版暂不使用）
    :param vul_function: 漏洞函数名
    :param line: 行号
    :param file_path: 文件路径
    :param repair_functions: 修复函数列表
    :param controlled_params: 可控参数列表
    :param isexternal: 是否外部调用
    :return: (code, cp, expr_lineno, chain)
    """
    try:
        code, cp, src_ln = parameters_back(param, [], int(line), file_path,
                                    repair_functions, controlled_params)

        # 构建 chain
        source_lines = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                source_lines = f.readlines()
        except Exception:
            pass

        source_ln = src_ln if src_ln else int(line)
        chain = ["{}:{}".format(source_ln, source_lines[source_ln - 1].strip() if source_ln <= len(source_lines) else param)]

        return code, cp, source_ln, chain

    except Exception:
        logger.warning("[AST][Python] analysis_params error: {}".format(traceback.format_exc()))
        return -1, None, line, []
