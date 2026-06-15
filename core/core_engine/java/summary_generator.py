#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Java 函数摘要生成器
    ~~~~~~~~~~~~~~~~~~~
    用 javalang 库解析 Java 源文件，提取每个方法的返回值数据流摘要。
    摘要只记录数据流事实，不做安全判定。

    :author:    LoRexxar <LoRexxar@gmail.com>
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""
from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Set

import javalang
import javalang.tree

from core.core_engine.function_summary import FileSummary, FunctionSummary, ReturnFlowItem
from utils.log import logger

_MAX_TRACE_DEPTH = 10

# 模块级摘要注册表，用于跨函数递归分析
_summary_registry: Dict[str, FunctionSummary] = {}


def lookup_summary(func_name: str) -> Optional[FunctionSummary]:
    """Query function summary. Try exact match first, then fallback to short name."""
    # Exact match first (caller may pass qualified name like ClassName.methodName)
    result = _summary_registry.get(func_name)
    if result:
        return result
    # Extract short name for fallback
    if "::" in func_name:
        short_name = func_name.split("::")[-1]
    elif "." in func_name:
        short_name = func_name.split(".")[-1]
    else:
        short_name = func_name
    return _summary_registry.get(short_name)


# ---------------------------------------------------------------------------
# 辅助工具函数
# ---------------------------------------------------------------------------

def _expr_to_str(node) -> str:
    """将 javalang AST 节点转为文本表示。

    递归拼接各类型节点，模仿原始 Java 代码片段。
    """
    if node is None:
        return "..."
    # 字面量
    if isinstance(node, javalang.tree.Literal):
        return str(node.value)
    # 成员引用（变量名）
    if isinstance(node, javalang.tree.MemberReference):
        parts = []
        if node.qualifier:
            q = _resolve_qualifier(node.qualifier)
            parts.append(q if isinstance(q, str) else _expr_to_str(q))
        parts.append(node.member)
        return ".".join(parts) if parts else node.member
    # this 引用
    if isinstance(node, javalang.tree.This):
        return "this"
    # 方法调用
    if isinstance(node, javalang.tree.MethodInvocation):
        parts = []
        if node.qualifier:
            q = _resolve_qualifier(node.qualifier)
            parts.append(q if isinstance(q, str) else _expr_to_str(q))
        parts.append(node.member)
        base = ".".join(parts) if parts else node.member
        args = ", ".join(_expr_to_str(a) for a in (node.arguments or []))
        return f"{base}({args})"
    # 二元运算
    if isinstance(node, javalang.tree.BinaryOperation):
        return f"{_expr_to_str(node.operandl)} {node.operator} {_expr_to_str(node.operandr)}"
    # 赋值
    if isinstance(node, javalang.tree.Assignment):
        return f"{_expr_to_str(node.expressionl)} = {_expr_to_str(node.value)}"
    # 类型转换
    if isinstance(node, javalang.tree.Cast):
        type_name = node.type.name if hasattr(node.type, "name") else str(node.type)
        return f"({type_name}) {_expr_to_str(node.expression)}"
    # new 表达式
    if isinstance(node, javalang.tree.ClassCreator):
        type_name = node.type.name if hasattr(node.type, "name") else str(node.type)
        args = ", ".join(_expr_to_str(a) for a in (node.arguments or []))
        return f"new {type_name}({args})"
    # 三元表达式
    if isinstance(node, javalang.tree.TernaryExpression):
        return (
            f"{_expr_to_str(node.condition)}"
            f" ? {_expr_to_str(node.if_true)}"
            f" : {_expr_to_str(node.if_false)}"
        )
    # 字符串回退
    try:
        return str(node)
    except Exception:
        return "..."


def _resolve_qualifier(qualifier):
    """将 qualifier（可能是字符串或 AST 节点）统一返回。"""
    # javalang 中 qualifier 可能是 str 或 AST 节点对象
    if isinstance(qualifier, str):
        # 字符串形式直接返回，由调用方按 str 处理
        return qualifier
    return qualifier


def _get_line(node) -> int:
    """从节点获取行号，返回 0 表示无法获取。"""
    pos = getattr(node, "position", None)
    if pos is not None:
        # javalang position 通常是 (line, column) 元组或 Position 对象
        try:
            return pos[0] if hasattr(pos, "__getitem__") else getattr(pos, "line", 0)
        except (TypeError, IndexError):
            pass
    return 0


def _is_literal(node) -> bool:
    """判断节点是否为字面量。"""
    if isinstance(node, javalang.tree.Literal):
        return True
    return False


# ---------------------------------------------------------------------------
# 赋值收集
# ---------------------------------------------------------------------------

def _find_assignments(stmts) -> Dict[str, object]:
    """在方法体语句列表中收集赋值和局部变量声明的左值 -> 右值节点映射。

    仅记录 identifier = expr 形式的简单赋值。
    """
    assignments: Dict[str, object] = {}
    if stmts is None:
        return assignments

    for stmt in stmts:
        # 局部变量声明: Type varName = expr;
        if isinstance(stmt, javalang.tree.LocalVariableDeclaration):
            for declarator in (stmt.declarators or []):
                if declarator.initializer is not None:
                    assignments[declarator.name] = declarator.initializer

        # 表达式语句中的赋值: var = expr;
        elif isinstance(stmt, javalang.tree.StatementExpression):
            if isinstance(stmt.expression, javalang.tree.Assignment):
                assign = stmt.expression
                var_name = _get_member_name(assign.expressionl)
                if var_name:
                    assignments[var_name] = assign.value

        # 递归进入控制流块（if / for / while / try / do / switch）
        _collect_assignments_from_block(stmt, assignments)

    return assignments


def _collect_assignments_from_block(stmt, assignments: Dict[str, object]) -> None:
    """从控制流语句中递归收集赋值。"""
    # IfStatement
    if isinstance(stmt, javalang.tree.IfStatement):
        _find_assignments_in_node(stmt.then_statement, assignments)
        if stmt.else_statement:
            _find_assignments_in_node(stmt.else_statement, assignments)

    # ForStatement
    elif isinstance(stmt, javalang.tree.ForStatement):
        if stmt.body:
            _find_assignments_in_node(stmt.body, assignments)

    # WhileStatement
    elif isinstance(stmt, javalang.tree.WhileStatement):
        if stmt.body:
            _find_assignments_in_node(stmt.body, assignments)

    # DoStatement
    elif isinstance(stmt, javalang.tree.DoStatement):
        if stmt.body:
            _find_assignments_in_node(stmt.body, assignments)

    # TryStatement
    elif isinstance(stmt, javalang.tree.TryStatement):
        if stmt.block:
            _find_assignments_in_node_list(stmt.block, assignments)
        for catch in (stmt.catches or []):
            if catch.block:
                _find_assignments_in_node_list(catch.block, assignments)
        if stmt.finally_block:
            _find_assignments_in_node_list(stmt.finally_block, assignments)

    # SwitchStatement
    elif isinstance(stmt, javalang.tree.SwitchStatement):
        for case in (stmt.cases or []):
            _find_assignments_in_node_list(case.statements, assignments)

    # SynchronizedStatement
    elif isinstance(stmt, javalang.tree.SynchronizedStatement):
        if stmt.block:
            _find_assignments_in_node_list(stmt.block, assignments)


def _find_assignments_in_node(node, assignments: Dict[str, object]) -> None:
    """处理可能是 BlockStatement 或单条语句的节点。"""
    if node is None:
        return
    if isinstance(node, javalang.tree.BlockStatement):
        _find_assignments_in_node_list(node.statements, assignments)
    elif isinstance(node, list):
        _find_assignments_in_node_list(node, assignments)
    else:
        # 单条语句，包装成列表处理
        _find_assignments([node], assignments)


def _find_assignments_in_node_list(stmts, assignments: Dict[str, object]) -> None:
    """在语句列表中递归收集赋值。"""
    if stmts is None:
        return
    for stmt in stmts:
        if isinstance(stmt, javalang.tree.LocalVariableDeclaration):
            for declarator in (stmt.declarators or []):
                if declarator.initializer is not None:
                    assignments[declarator.name] = declarator.initializer
        elif isinstance(stmt, javalang.tree.StatementExpression):
            if isinstance(stmt.expression, javalang.tree.Assignment):
                assign = stmt.expression
                var_name = _get_member_name(assign.expressionl)
                if var_name:
                    assignments[var_name] = assign.value
        # 递归进入控制流块
        _collect_assignments_from_block(stmt, assignments)


def _get_member_name(node) -> Optional[str]:
    """从表达式节点提取变量名（仅处理简单 MemberReference）。"""
    if isinstance(node, javalang.tree.MemberReference):
        return node.member
    return None


# ---------------------------------------------------------------------------
# return 语句遍历
# ---------------------------------------------------------------------------

def _walk_for_returns(stmts, result: list) -> None:
    """递归遍历方法体语句列表，收集所有 ReturnStatement 的表达式。"""
    if stmts is None:
        return

    for stmt in stmts:
        if isinstance(stmt, javalang.tree.ReturnStatement):
            if stmt.expression is not None:
                result.append(stmt.expression)

        # 进入 BlockStatement（if/for/while/try 的子块）
        elif isinstance(stmt, javalang.tree.BlockStatement):
            _walk_for_returns(stmt.statements, result)

        # IfStatement
        elif isinstance(stmt, javalang.tree.IfStatement):
            _walk_for_returns_node(stmt.then_statement, result)
            if stmt.else_statement:
                _walk_for_returns_node(stmt.else_statement, result)

        # ForStatement
        elif isinstance(stmt, javalang.tree.ForStatement):
            if stmt.body:
                _walk_for_returns_node(stmt.body, result)

        # WhileStatement
        elif isinstance(stmt, javalang.tree.WhileStatement):
            if stmt.body:
                _walk_for_returns_node(stmt.body, result)

        # DoStatement
        elif isinstance(stmt, javalang.tree.DoStatement):
            if stmt.body:
                _walk_for_returns_node(stmt.body, result)

        # TryStatement
        elif isinstance(stmt, javalang.tree.TryStatement):
            if stmt.block:
                _walk_for_returns(stmt.block, result)
            for catch in (stmt.catches or []):
                if catch.block:
                    _walk_for_returns(catch.block, result)
            if stmt.finally_block:
                _walk_for_returns(stmt.finally_block, result)

        # SwitchStatement
        elif isinstance(stmt, javalang.tree.SwitchStatement):
            for case in (stmt.cases or []):
                _walk_for_returns(case.statements, result)

        # SynchronizedStatement
        elif isinstance(stmt, javalang.tree.SynchronizedStatement):
            if stmt.block:
                _walk_for_returns(stmt.block, result)


def _walk_for_returns_node(node, result: list) -> None:
    """处理可能是 BlockStatement 或单条语句的节点。"""
    if node is None:
        return
    if isinstance(node, javalang.tree.BlockStatement):
        _walk_for_returns(node.statements, result)
    elif isinstance(node, list):
        _walk_for_returns(node, result)
    else:
        # 单条语句
        if isinstance(node, javalang.tree.ReturnStatement):
            if node.expression is not None:
                result.append(node.expression)
        else:
            _walk_for_returns([node], result)


# ---------------------------------------------------------------------------
# 数据流追踪
# ---------------------------------------------------------------------------

def _trace_dataflow(
    expr,
    param_names: List[str],
    assignments: Optional[Dict[str, object]] = None,
    visited: Optional[Set[int]] = None,
    depth: int = 0,
) -> dict:
    """从表达式节点反向追踪数据流。

    返回字典包含 origin, origin_type, dep_params, path 四个字段。
    不做安全判定，只记录数据流事实。
    """
    if visited is None:
        visited = set()
    if depth > _MAX_TRACE_DEPTH:
        return {
            "origin": _expr_to_str(expr),
            "origin_type": "unknown",
            "dep_params": [],
            "path": [],
        }

    node_id = id(expr)
    if node_id in visited:
        return {
            "origin": _expr_to_str(expr),
            "origin_type": "unknown",
            "dep_params": [],
            "path": [],
        }
    visited = visited | {node_id}

    if assignments is None:
        assignments = {}

    # 1. 字面量
    if _is_literal(expr):
        return {
            "origin": _expr_to_str(expr),
            "origin_type": "literal",
            "dep_params": [],
            "path": [],
        }

    # 2. 成员引用（变量名）
    if isinstance(expr, javalang.tree.MemberReference):
        name = expr.member
        if name in param_names:
            idx = param_names.index(name)
            return {
                "origin": name,
                "origin_type": "param",
                "dep_params": [idx],
                "path": [],
            }

        # 检查 qualifier 是否为参数引用（如 this.field 或 req.param）
        if expr.qualifier:
            qualifier_str = _expr_to_str(_resolve_qualifier(expr.qualifier)) if not isinstance(expr.qualifier, str) else expr.qualifier
            if qualifier_str in param_names:
                idx = param_names.index(qualifier_str)
                return {
                    "origin": _expr_to_str(expr),
                    "origin_type": "param",
                    "dep_params": [idx],
                    "path": [],
                }

        # 检查赋值链
        if name in assignments:
            rhs_node = assignments[name]
            result = _trace_dataflow(rhs_node, param_names, assignments, visited, depth + 1)
            result["path"].append({
                "node": name,
                "type": "assign",
                "line": _get_line(rhs_node),
            })
            return result

        return {
            "origin": name,
            "origin_type": "global",
            "dep_params": [],
            "path": [],
        }

    # 3. this 引用
    if isinstance(expr, javalang.tree.This):
        return {
            "origin": "this",
            "origin_type": "global",
            "dep_params": [],
            "path": [],
        }

    # 4. 方法调用 MethodInvocation
    if isinstance(expr, javalang.tree.MethodInvocation):
        # 构建函数名：qualifier.member 或 member
        if expr.qualifier:
            qualifier_str = _expr_to_str(_resolve_qualifier(expr.qualifier)) if not isinstance(expr.qualifier, str) else expr.qualifier
            func_name = f"{qualifier_str}.{expr.member}"
        else:
            func_name = expr.member

        dep_params: List[int] = []

        # 追踪 qualifier 部分
        if expr.qualifier and not isinstance(expr.qualifier, str):
            sub = _trace_dataflow(
                expr.qualifier, param_names, assignments,
                visited, depth + 1,
            )
            dep_params.extend(sub.get("dep_params", []))
        elif isinstance(expr.qualifier, str) and expr.qualifier in param_names:
            dep_params.append(param_names.index(expr.qualifier))

        # 收集参数的数据流信息（用于递归展开时做参数映射）
        arg_flows: List[dict] = []
        for arg in (expr.arguments or []):
            sub = _trace_dataflow(
                arg, param_names, assignments,
                visited, depth + 1,
            )
            dep_params.extend(sub.get("dep_params", []))
            arg_flows.append(sub)

        # 递归查摘要注册表，展开自定义方法调用
        short_name = func_name.split(".")[-1] if "." in func_name else func_name
        callee_summary = _summary_registry.get(short_name)

        if callee_summary and callee_summary.return_flow and depth < _MAX_TRACE_DEPTH:
            expanded_deps: List[int] = []
            for rf in callee_summary.return_flow:
                for callee_param_idx in rf.dep_params:
                    if callee_param_idx < len(arg_flows):
                        expanded_deps.extend(arg_flows[callee_param_idx].get("dep_params", []))

            if expanded_deps:
                all_deps = list(dict.fromkeys(dep_params + expanded_deps))
                line = _get_line(expr)
                return {
                    "origin": func_name,
                    "origin_type": "call",
                    "dep_params": all_deps,
                    "path": [{
                        "node": func_name,
                        "type": "call",
                        "line": line,
                    }],
                    "expanded_from": short_name,
                }

        line = _get_line(expr)
        return {
            "origin": func_name,
            "origin_type": "call",
            "dep_params": list(dict.fromkeys(dep_params)),
            "path": [{
                "node": func_name,
                "type": "call",
                "line": line,
            }],
        }

    # 5. 二元运算 BinaryOperation
    if isinstance(expr, javalang.tree.BinaryOperation):
        dep_params: List[int] = []
        path: List[dict] = []
        for side in (expr.operandl, expr.operandr):
            sub = _trace_dataflow(
                side, param_names, assignments,
                visited, depth + 1,
            )
            dep_params.extend(sub.get("dep_params", []))
            if sub.get("path"):
                path.extend(sub["path"])

        return {
            "origin": _expr_to_str(expr),
            "origin_type": "unknown",
            "dep_params": list(dict.fromkeys(dep_params)),
            "path": path,
        }

    # 6. 赋值 Assignment
    if isinstance(expr, javalang.tree.Assignment):
        return _trace_dataflow(
            expr.value, param_names, assignments,
            visited, depth + 1,
        )

    # 7. 类型转换 Cast
    if isinstance(expr, javalang.tree.Cast):
        return _trace_dataflow(
            expr.expression, param_names, assignments,
            visited, depth + 1,
        )

    # 8. new 表达式 ClassCreator
    if isinstance(expr, javalang.tree.ClassCreator):
        dep_params: List[int] = []
        for arg in (expr.arguments or []):
            sub = _trace_dataflow(
                arg, param_names, assignments,
                visited, depth + 1,
            )
            dep_params.extend(sub.get("dep_params", []))
        return {
            "origin": _expr_to_str(expr),
            "origin_type": "call",
            "dep_params": list(dict.fromkeys(dep_params)),
            "path": [],
        }

    # 9. 三元表达式 TernaryExpression
    if isinstance(expr, javalang.tree.TernaryExpression):
        dep_params: List[int] = []
        for branch in (expr.if_true, expr.if_false):
            sub = _trace_dataflow(
                branch, param_names, assignments,
                visited, depth + 1,
            )
            dep_params.extend(sub.get("dep_params", []))
        return {
            "origin": _expr_to_str(expr),
            "origin_type": "unknown",
            "dep_params": list(dict.fromkeys(dep_params)),
            "path": [],
        }

    # 其他情况
    return {
        "origin": _expr_to_str(expr),
        "origin_type": "unknown",
        "dep_params": [],
        "path": [],
    }


# ---------------------------------------------------------------------------
# 方法分析
# ---------------------------------------------------------------------------

def _collect_methods(type_decl, result: List[FunctionSummary], class_prefix: str = "") -> None:
    """递归收集类（含内部类、接口）中的方法。

    :param type_decl: 类/接口/枚举声明节点
    :param result: 收集结果列表
    :param class_prefix: 外层类名前缀（用于内部类拼接全限定名）
    """
    type_name = type_decl.name
    full_class_name = f"{class_prefix}.{type_name}" if class_prefix else type_name

    # 遍历类体，收集方法和内部类
    if hasattr(type_decl, "methods") and type_decl.methods:
        for method in type_decl.methods:
            fn_summary = _analyze_method(method, full_class_name)
            if fn_summary:
                result.append(fn_summary)

    # 构造方法
    if hasattr(type_decl, "constructors") and type_decl.constructors:
        for constructor in type_decl.constructors:
            fn_summary = _analyze_method(constructor, full_class_name)
            if fn_summary:
                result.append(fn_summary)

    # 内部类 / 接口 / 枚举
    if hasattr(type_decl, "body") and type_decl.body:
        for body_item in type_decl.body:
            if isinstance(body_item, javalang.tree.ClassDeclaration):
                _collect_methods(body_item, result, full_class_name)
            elif isinstance(body_item, javalang.tree.InterfaceDeclaration):
                _collect_methods(body_item, result, full_class_name)
            elif isinstance(body_item, javalang.tree.EnumDeclaration):
                _collect_methods(body_item, result, full_class_name)


def _analyze_method(method_node, class_name: str = "") -> Optional[FunctionSummary]:
    """分析单个方法声明，生成摘要。

    方法名格式 "ClassName.methodName"，内部类为
    "OuterClass.InnerClass.methodName"。

    :param method_node: MethodDeclaration 或 ConstructorDeclaration 节点
    :param class_name: 所属类名（含外部类前缀）
    """
    method_name = method_node.name
    full_name = f"{class_name}.{method_name}" if class_name else method_name

    # 提取参数列表（Java 方法参数不含 this，无需跳过）
    params: List[str] = []
    if method_node.parameters:
        for param in method_node.parameters:
            if isinstance(param, javalang.tree.FormalParameter):
                params.append(param.name)
            elif isinstance(param, javalang.tree.InferredFormalParameter):
                params.append(param.name)

    # 行号范围
    start_line = _get_line(method_node)
    # javalang 没有直接的 end_lineno，用 position 的 line 作为起始
    # 尝试从方法体的最后一条语句估算结束行
    end_line = start_line
    if method_node.body:
        for stmt in method_node.body:
            stmt_line = _get_line(stmt)
            if stmt_line > end_line:
                end_line = stmt_line

    # 收集方法体中的赋值
    assignments = _find_assignments(method_node.body)

    # 找到所有 return 语句中的表达式
    return_exprs: List[object] = []
    if method_node.body:
        _walk_for_returns(method_node.body, return_exprs)

    # 构建返回值数据流
    return_flow: List[ReturnFlowItem] = []
    for order, expr in enumerate(return_exprs):
        flow = _trace_dataflow(expr, params, assignments)
        return_flow.append(ReturnFlowItem(
            order=order,
            return_index=0,
            origin=flow["origin"],
            origin_type=flow["origin_type"],
            dep_params=flow.get("dep_params", []),
            path=flow.get("path", []),
        ))

    return FunctionSummary(
        name=full_name,
        params=params,
        line_range=(start_line, end_line),
        return_flow=return_flow,
    )


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

def generate_file_summaries(file_path: str, file_content: str) -> FileSummary:
    """解析一个 Java 文件，生成函数摘要。

    用 javalang 库解析 Java AST，遍历所有顶层类（含内部类）中的方法，
    对每个方法提取返回值数据流。

    :param file_path: 文件路径，用于记录在摘要中
    :param file_content: Java 源文件内容
    :return: FileSummary 实例，解析失败时返回空摘要
    """
    content_hash = hashlib.sha256(file_content.encode("utf-8")).hexdigest()

    try:
        tree = javalang.parse.parse(file_content)
    except Exception as e:
        logger.warning(f"解析 Java 文件失败 {file_path}: {e}")
        return FileSummary(file=file_path, content_hash=content_hash, functions=[])

    functions: List[FunctionSummary] = []
    for type_decl in (tree.types or []):
        _collect_methods(type_decl, functions)

    return FileSummary(
        file=file_path,
        content_hash=content_hash,
        functions=functions,
    )


def generate_summaries_for_target(
    target_path: str,
    files_dict: Dict[str, str],
) -> Dict[str, FileSummary]:
    """便捷入口：遍历所有 Java 文件，生成摘要。

    两遍处理：
    1. 第一遍：生成所有文件的摘要，注册到全局注册表
    2. 第二遍：对有自定义方法调用的函数做二次分析（可递归展开）

    :param target_path: 扫描目标路径（仅用于日志）
    :param files_dict: {file_path: file_content} 字典
    :return: {file_path: FileSummary} 字典
    """
    global _summary_registry
    _summary_registry = {}

    summaries: Dict[str, FileSummary] = {}

    # 第一遍：生成所有摘要并注册
    for file_path, content in files_dict.items():
        if not file_path.endswith(".java"):
            continue
        logger.debug(f"生成函数摘要: {file_path}")
        fs = generate_file_summaries(file_path, content)
        summaries[file_path] = fs
        for fn in fs.functions:
            # 用全限定名注册
            _summary_registry[fn.name] = fn
            # 同时用短名注册（方法名），方便跨函数调用时通过短名查找
            short_name = fn.name.split(".")[-1]
            if short_name not in _summary_registry:
                _summary_registry[short_name] = fn

    # 第二遍：对有自定义方法调用的函数做二次分析
    for file_path, content in files_dict.items():
        if not file_path.endswith(".java"):
            continue
        old_fs = summaries[file_path]
        new_fs = generate_file_summaries(file_path, content)
        changed = False
        for i, fn in enumerate(new_fs.functions):
            if fn.return_flow:
                old_fn = old_fs.functions[i]
                if len(fn.return_flow) != len(old_fn.return_flow):
                    old_fs.functions[i] = fn
                    changed = True
                else:
                    for j, rf in enumerate(fn.return_flow):
                        if rf.dep_params != old_fn.return_flow[j].dep_params:
                            old_fs.functions[i] = fn
                            changed = True
                            break
        if changed:
            summaries[file_path] = old_fs

    logger.debug(f"函数摘要生成完成: {len(summaries)} 个文件, {len(_summary_registry)} 个函数")
    return summaries
