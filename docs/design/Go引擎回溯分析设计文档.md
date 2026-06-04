# Go 引擎回溯分析设计文档

## 一、引擎概览

### 1.1 技术选型

Go 引擎是 Kunlun-M 中**唯一使用 tree-sitter** 做源码解析的语言引擎。其他引擎使用各自语言的 Python 解析库（ljavalang、lphply、lesprima）或 Python 内置 `ast` 模块。

**核心依赖：**
- `tree-sitter` + `tree-sitter-go`：Go 源码 AST 解析
- `tree-sitter` 的 Python binding 提供了 `Language`, `Parser` 等 API

**文件结构：**

```
core/core_engine/go/
├── __init__.py              # 包初始化
├── engine.py                # 引擎注册（730B）
├── parser.py                # 核心回溯分析引擎（2442行，91KB）
├── _ast_trace.py            # 纯 AST 追踪引擎（965行，38KB）
├── builtin_knowledge.py     # Go 内置知识库（36KB）
└── summary_generator.py     # 函数摘要生成器（21KB）
```

### 1.2 可控源定义

Go 引擎定义了丰富的可控源列表，涵盖标准库和主流 Web 框架：

**标准库可控源：**
```python
GO_CONTROLLED_SOURCES = [
    # net/http
    "r.URL.Query", "r.FormValue", "r.PostFormValue", "r.FormFile",
    "r.Header.Get", "r.Cookie", "r.Host", "r.RequestURI",
    "req.URL.Query", "req.FormValue",  # 别名
    # os
    "os.Getenv", "os.Args",
    # flag
    "flag.Arg", "flag.Args",
    # io
    "ioutil.ReadAll", "io.ReadAll",
    # fmt
    "fmt.Scanf", "fmt.Scanln",
]
```

**Web 框架可控源（4大框架）：**
- **Gin**：`c.Query`, `c.PostForm`, `c.Param`, `c.Request.URL.Query`
- **Echo**：`echo.QueryParam`, `echo.FormValue`, `echo.Param`
- **Fiber**：`fiber.Ctx.Query`, `fiber.Ctx.Params`, `fiber.Ctx.FormValue`
- **Beego**：`beego.Input.Query`, `this.GetString`, `this.GetFile`

### 1.3 Sink 定义

Go 引擎的 sink 定义在 `GO_SENSITIVE_SINKS` 中，包括：
- **命令执行**：`exec.Command`, `exec.CommandContext`, `os.StartProcess`
- **文件操作**：`os.Open`, `os.Create`, `os.Remove`, `os.MkdirAll`
- **网络操作**：`net.Dial`, `net.Listen`, `net.DialTimeout`
- **SQL 操作**：`db.Query`, `db.Exec`, `db.Prepare`
- **模板注入**：`template.Execute`, `template.ExecuteTemplate`

---

## 二、AST 解析与缓存层

### 2.1 tree-sitter Go AST 解析

Go 引擎使用 tree-sitter-go 语法规则解析 Go 源码，获得完整的 CST（具体语法树）。tree-sitter 的优势在于：
1. **增量解析**：支持部分重新解析（虽然当前实现未使用）
2. **错误恢复**：语法错误不会导致解析失败，返回部分 AST
3. **精确节点定位**：每个节点都有 `start_point`/`end_point`（行列号）

```python
def _parse_go_ast(file_path):
    """解析 Go 文件为 tree-sitter AST，带缓存。"""
    if file_path in _ast_cache:
        return _ast_cache[file_path]
    try:
        with open(file_path, 'rb') as f:
            source_code = f.read()
        parser = Parser(Language(_go_language))
        tree = parser.parse(source_code)
        _ast_cache[file_path] = tree
        return tree
    except Exception:
        return None
```

**关键 AST 节点类型（tree-sitter-go）：**
- `function_declaration` / `method_declaration`：函数/方法定义
- `call_expression`：函数调用
- `short_var_declaration`：`x := expr` 短变量声明
- `assignment_statement`：`x = expr` 赋值
- `var_declaration`：`var x Type = expr` 变量声明
- `if_statement` / `for_statement` / `expression_switch_statement`：控制流
- `binary_expression`：二元表达式（含 `&&`, `||`, `+` 等）
- `selector_expression`：`a.b` 选择器表达式
- `index_expression` / `slice_expression`：索引/切片
- `type_conversion_expression`：`string(x)` 类型转换
- `return_statement`：return 语句

### 2.2 多级缓存体系

Go 引擎维护了 4 个模块级缓存：

| 缓存变量 | 类型 | 用途 | 键 |
|---------|------|------|---|
| `_ast_cache` | `dict[str, Tree]` | AST 解析结果 | 文件路径 |
| `_import_cache` | `dict[str, dict]` | import 映射 | 文件路径 |
| `_package_name_cache` | `dict[str, str]` | Go 包名 | 文件路径 |
| `_func_def_index` | `dict[(str,str), tuple]` | 函数定义索引 | (文件路径, 函数名) |

```python
# 全局缓存
_ast_cache = {}
_import_cache = {}
_package_name_cache = {}
_func_def_index = {}          # (file_path, func_name) -> (formal_params, body_lines, def_lineno)
_scan_function_stack = []     # 递归防护栈
_ast_object_singleton = None # 引擎全局对象引用
_summaries_initialized = False # 摘要初始化标志
```

### 2.3 Import 路径解析

Go 的 import 系统是跨文件追踪的基础。引擎通过 import_map 将包别名映射到本地文件：

```python
def _parse_go_imports(file_path):
    """
    解析 Go 文件的 import 声明，建立包别名→本地文件列表映射。
    
    import (
        "github.com/user/project/pkg"  // 包名: project
        alias "github.com/user/pkg2"    // 包名: alias
    )
    
    返回: {包别名: [本地文件路径列表], ...}
    """
```

**跨文件搜索策略（三层优先级）：**
1. **import_map 精确搜索**：先解析当前文件的 import，用包别名→本地文件映射缩小范围
2. **_func_def_index 索引搜索**：跨文件预建索引中查找
3. **暴力搜索 fallback**：遍历 `pre_result` 中所有 Go 文件

---

## 三、扫描入口：scan_parser

### 3.1 入口函数签名

```python
def scan_parser(rule_match, vul_lineno, file_path,
                repair_functions=None, controlled_params=None,
                svid=None, is_config_vuln=False):
```

### 3.2 完整扫描流程

```
scan_parser(rule_match, vul_lineno, file_path)
│
├─ 1. 预建函数定义索引（仅首次）
│   ├─ _build_func_def_index(file_path)         # 当前文件
│   └─ _build_func_def_index_cross_file()       # 跨文件
│
├─ 2. 初始化函数摘要
│   └─ _init_function_summaries(file_path)
│
├─ 3. 精确匹配规则函数名
│   ├─ 清理正则转义 (\.→.  \(→()
│   ├─ 精确匹配：clean_func in line_text
│   └─ 模糊匹配：parts 长度>2 的部分出现在行中
│
├─ 4. tree-sitter 解析 + AST 节点提取
│   ├─ _parse_go_ast(file_path)
│   ├─ _find_call_at_line(ast_tree, vul_lineno, matched_func)
│   └─ _get_call_args_from_ast(call_node)
│
├─ 5. 知识库安全检查
│   └─ lookup_builtin(matched_func) → safe=True → 直接返回 code=-1
│
├─ 6. 遍历 AST 参数节点
│   ├─ 跳过字面量节点
│   ├─ _collect_identifiers_from_ast(arg_node)
│   └─ 对每个变量名：
│       ├─ 直接可控检查 → _is_controllable_source()
│       └─ 反向追踪 → _trace_variable_in_lines()
│           ├─ code=1 → 漏洞成立
│           ├─ code=2 → 已修复
│           ├─ code=3 → 未确认
│           └─ code=-1 → 不可控
│
└─ 7. 返回结果列表
    └─ [{'code': int, 'chain': [(type, name, file, lineno), ...]}]
```

### 3.3 结果编码

与所有引擎一致：

| code | 含义 |
|------|------|
| 1 | 可控，漏洞成立 |
| 2 | 已修复（经修复函数处理） |
| 3 | 未确认（deps 追踪未完成） |
| -1 | 不可控 |
| 4 | 配置型漏洞 |

---

## 四、核心回溯分析：_trace_variable_in_lines

### 4.1 双层架构：缓存层 + 实现层

Go 引擎的变量追踪分为两层：

```python
# 缓存包装层
def _trace_variable_in_lines(file_path, var_name, from_line, to_line,
                              repair_functions, controlled_params, depth, max_depth):
    # 顶层调用查/写缓存
    if depth == 0:
        cached = _trace_cache.get(file_path, var_name, to_line)
        if cached: return cached
    
    code, source_lineno = _trace_variable_in_lines_impl(...)
    
    if depth == 0 and code in (1, 2, -1):
        _trace_cache.put(file_path, var_name, to_line, (code, [], source_lineno))
    
    return (code, source_lineno)

# 实际实现层
def _trace_variable_in_lines_impl(file_path, var_name, from_line, to_line,
                                   repair_functions, controlled_params, depth, max_depth):
    # 纯 tree-sitter AST 实现
```

**缓存策略：**
- 仅缓存 `depth=0` 的顶层调用（避免缓存中间结果）
- 仅缓存确定性结果（code=1/2/-1），不缓存未确认结果（code=3）

### 4.2 追踪流程

```
_trace_variable_in_lines_impl(file_path, var_name, to_line)
│
├─ 1. 深度检查：depth > max_depth → return (-1, 0)
│
├─ 2. AST 解析：_parse_go_ast(file_path)
│
├─ 3. 定位函数体
│   ├─ _find_enclosing_function(tree, to_line)
│   │   └─ 返回 (func_name, params_node, func_start, func_end)
│   └─ 找到函数的 block 节点和 statement_list
│
├─ 4. 反向遍历语句列表（最近赋值优先）
│   └─ for i in reversed(stmt_list.children):
│       └─ trace_go_stmt(var_name, stmt, ...)
│           ├─ 赋值语句 → _check_assignment_node + trace_go_expr
│           ├─ if 语句 → 分支约束检查 + 递归目标分支体
│           ├─ for 语句 → while 约束检查 + 体搜索
│           ├─ switch → case 分支约束检查
│           └─ 其他 → 递归子块
│
├─ 5. 未找到赋值 → 检查是否是函数形参
│   ├─ _get_formal_param_names_ast(params_node)
│   └─ var_name in formal_param_names → 搜索调用点
│       ├─ _trace_param_at_call_sites_ast(当前文件)
│       ├─ import_map 跨文件搜索
│       └─ 暴力搜索 fallback
│
└─ 6. 全部失败 → return (-1, 0)
```

### 4.3 AST 追踪与文本追踪的双轨设计

Go 引擎同时保留了 AST 追踪和文本追踪两套实现：

**AST 追踪（主路径，_ast_trace.py）：**
- `trace_go_stmt`：按语句类型分派
- `trace_go_expr`：按表达式类型分派
- 完全基于 tree-sitter 节点类型，无正则

**文本追踪（fallback，parser.py）：**
- `_text_trace_variable`：正则匹配赋值，逐行向上搜索
- `_trace_param_at_call_sites`：正则搜索调用点
- 仅在 AST 解析失败或作为兼容性补充时使用

---

## 五、纯 AST 追踪引擎：_ast_trace.py

### 5.1 设计理念

`_ast_trace.py` 是 Go 引擎的纯 AST 追踪引擎，从 parser.py 中抽取出来形成独立模块。它参考 Python 引擎的 `_trace_stmt` / `_trace_expr` 模式，按 AST 节点类型分派分析。

**设计原则：**
1. 完全移除正则表达式
2. 所有分析基于 tree-sitter 节点类型判断
3. 语句层（trace_go_stmt）和表达式层（trace_go_expr）分离
4. 分支约束与 Python 引擎共享 `BranchConstraint` 类

### 5.2 trace_go_stmt：语句层分派

```python
def trace_go_stmt(var_name, stmt_node, file_path, vul_lineno, to_line,
                  repair_functions, controlled_params, depth, max_depth,
                  function_back_go_fn, trace_variable_fn):
```

**语句类型处理矩阵：**

| 语句类型 | 处理方式 |
|---------|---------|
| `short_var_declaration` (`:=`) | 提取 LHS/RHS → `trace_go_expr` |
| `assignment_statement` (`=`) | 提取 LHS/RHS → `trace_go_expr` |
| `var_declaration` (`var`) | 提取 var_spec → `trace_go_expr` |
| `if_statement` | 分支约束检查 + 只递归目标分支体 |
| `for_statement` | while 约束检查 / range 迭代变量分析 |
| `expression_switch_statement` | case 分支约束检查 |
| `type_switch_statement` | type case 处理 |
| `expression_statement` | 内部可能包含赋值，递归处理 |

### 5.3 trace_go_expr：表达式层分派

```python
def trace_go_expr(var_name, expr_node, file_path, lineno, to_line,
                  repair_functions, controlled_params, depth, max_depth,
                  function_back_go_fn, trace_variable_fn):
```

**表达式类型处理矩阵：**

| 表达式类型 | 处理方式 |
|-----------|---------|
| `call_expression` | → `_trace_call_expr`（知识库/passthrough/deps） |
| `binary_expression` | → `_trace_binary_expr`（字符串拼接，跳过操作符和字面量） |
| `identifier` | 直接可控检查或 `trace_variable_fn` 递归 |
| `selector_expression` (`a.b`) | 检查基础变量可控性或追踪 |
| `index_expression` (`a[i]`) | 追踪基础对象 |
| `type_conversion_expression` | 递归追踪转换参数 |
| `unary_expression` (`!x`, `-x`) | 跳过运算符，追踪操作数 |
| `parenthesized_expression` | 解包，追踪内部表达式 |
| 字面量类型 | → `(-1, 0)` 安全 |
| 其他 | 收集标识符逐一追踪 |

### 5.4 _trace_call_expr：函数调用处理

```python
def _trace_call_expr(var_name, call_node, file_path, lineno, to_line, ...):
    func_name = _get_call_func_name(call_node)
    args = _get_call_args(call_node)
    
    # 1. 内置知识库检查
    knowledge = lookup_builtin(func_name)
    if knowledge and knowledge.get("safe") and not knowledge.get("passthrough"):
        return (-1, 0)  # 安全函数
    
    # 2. passthrough 函数：追踪所有非字面量参数
    if knowledge and knowledge.get("passthrough"):
        for arg_node in args:
            if not _is_literal_node_safe(arg_node):
                result = trace_go_expr(var_name, arg_node, ...)
                if result[0] in (1, 2): return result
        return (-1, 0)
    
    # 3. 未知函数 → 跨函数 deps 追踪
    fb_result = function_back_go_fn(func_name, args_str, lineno, file_path, ...)
    if code == 'deps' and caller_deps:
        for dep_var in caller_deps:
            result = trace_variable_fn(file_path, dep_var, ...)
            if result[0] in (1, 2): return result
        return (3, lineno)
```

---

## 六、跨函数追踪：function_back_go + deps 机制

### 6.1 function_back_go

```python
def function_back_go(func_name, call_args, vul_lineno, file_path,
                     repair_functions, controlled_params):
```

**执行流程：**

```
function_back_go(func_name, call_args, vul_lineno, file_path)
│
├─ 1. 递归防护：_scan_function_stack 检查
│   └─ func_name in _scan_function_stack → return (-1, [])
│
├─ 2. 内置知识库检查
│   └─ lookup_builtin(func_name) → safe=True → return (-1, [])
│
├─ 3. 函数摘要快速判定
│   └─ lookup_summary(func_name).return_flow → _judge_from_summary()
│
├─ 4. 函数定义查找（三级策略）
│   ├─ _func_def_index 索引（当前文件）
│   ├─ import_map 精确跨文件
│   │   └─ pkg.Func → import_map[pkg] → 候选文件列表
│   └─ 暴力搜索 pre_result fallback
│
├─ 5. 进入 callee 函数体检查 sink
│   └─ _trace_callee_body_for_sinks(...)
│       ├─ AST 解析 callee 文件
│       ├─ 在 callee 函数体中 walk 找 sink call
│       ├─ 建立形参→实参映射
│       └─ 对 sink 参数：
│           ├─ 直接可控 → return (1, [])
│           └─ 依赖调用者变量 → return ('deps', caller_vars)
│
└─ 6. 分析返回值依赖
    └─ _analyze_return_deps_go(...)
        ├─ 形参→实参映射
        ├─ 赋值链传播（AST + 正则双重）
        └─ return 语句分析
            ├─ 返回值是可控源 → (1, [])
            ├─ 返回值是修复函数 → (2, [])
            ├─ 返回值依赖可控形参 → (1, []) 或 ('deps', vars)
            └─ fallback → (3, [])
```

### 6.2 _trace_callee_body_for_sinks

这是 Go 引擎独有的设计，仿照 Python 引擎的 `_try_cross_file_trace`：

当 `function_back_go` 找到 callee 函数定义后，**先不分析返回值**，而是先检查函数体中是否有已知的 sink 调用。

```
_trace_callee_body_for_sinks(callee_file, callee_func, formal_params, call_args)
│
├─ 1. AST 解析 callee 文件
├─ 2. 找到 callee 函数定义节点
├─ 3. Walk 函数体，找 call_expression + lookup_builtin → safe=False
├─ 4. 建立形参→实参映射 arg_map
└─ 5. 对每个 sink 参数：
    ├─ 参数标识符 ∈ arg_map
    │   ├─ 实参直接可控 → return (1, [])
    │   └─ 提取实参变量名 → return ('deps', caller_vars)
    └─ 参数标识符 ∉ arg_map → 跳过（局部变量，与 caller 无关）
```

**设计意图：**
- 直接追踪 callee→sink 的数据流，而不是 callee→caller→sink 的间接路径
- 减少追踪深度，提高分析精度
- 类似于"内联展开" callee 的 sink 检查

### 6.3 _analyze_return_deps_go

当 `_trace_callee_body_for_sinks` 返回 `None`（未找到 sink），fallback 到返回值依赖分析：

```
_analyze_return_deps_go(formal_params, func_lines, call_args_str, file_path)
│
├─ 1. 解析实参，提取变量名
│
├─ 2. 建立形参→实参映射，标记可控形参
│   └─ arg_map: {formal_name: actual_expr}
│   └─ controllable_formal: 可控形参名集合
│
├─ 3. 赋值链传播（最多 3 轮迭代）
│   ├─ AST 传播：_propagate_assignments_ast
│   │   └─ walk AST，short_var_declaration / assignment_statement
│   │       如果 RHS 包含可控变量 → LHS 标记为可控
│   └─ 正则补充：匹配 `var := expr` / `var = expr`
│       如果 RHS 变量 ∈ controllable_local → LHS 加入
│
├─ 4. 分析 return 语句
│   ├─ 多返回值处理：取第一个（Go 允许多返回值）
│   ├─ 4a: return_expr 是可控源 → (1, [])
│   ├─ 4b: return_expr 是修复函数 → (2, [])
│   ├─ 4c: return_var_names & controllable_local ≠ ∅
│   │   ├─ arg_map[var] 可控 → (1, [])
│   │   └─ arg_map[var] 含变量名 → ('deps', vars)
│   └─ 4d: 文本匹配形参名（fallback）
│
└─ 5. Fallback: 返回调用者变量名 → ('deps', caller_var_names)
```

### 6.4 _judge_from_summary（摘要快速判定）

```python
def _judge_from_summary(summary, call_args_str, controlled_params):
    """
    根据函数摘要判定返回值可控性。
    对 return_flow 中每条路径独立判定，只要任意一条可控就返回 (1, [])。
    """
    for rf in summary.return_flow:
        if rf.origin_type == "param":
            # 返回值来自形参 → 检查实参
            for param_idx in rf.dep_params:
                actual_args = _split_args_respecting_parens(call_args_str)
                if _is_controllable_source(actual_args[param_idx], controlled_params):
                    return (1, [])
        elif rf.origin_type == "call":
            # 返回值来自方法调用 → 查知识库
            knowledge = lookup_builtin(rf.origin)
            if knowledge and (knowledge.get("passthrough") or knowledge.get("param_flow")):
                # 检查参数是否可控
                ...
        elif rf.origin_type == "global":
            if _is_controllable_source(rf.origin, controlled_params):
                return (1, [])
        elif rf.origin_type == "literal":
            continue  # 字面量不可控
    
    return (-1, [])  # 所有路径都不可控
```

---

## 七、形参追踪与跨文件调用点搜索

### 7.1 _trace_param_at_call_sites_ast

当变量是函数形参时，需要在调用点反向追踪实参：

```
_trace_param_at_call_sites_ast(func_name, param_name, file_path, tree)
│
├─ 1. AST walk 搜索所有 call_expression
│   └─ _get_call_func_name(node) contains func_name
│
├─ 2. 对每个调用点：
│   ├─ 获取实参列表 _get_call_args(call_node)
│   ├─ 获取形参列表
│   │   ├─ 先在当前文件找 func_def_node（AST 搜索）
│   │   └─ fallback: _func_def_index 跨文件搜索
│   ├─ 找到 param_name 在形参中的位置 param_idx
│   ├─ 获取对应实参 actual_arg[param_idx]
│   └─ 追踪实参：
│       ├─ identifier → _trace_variable_in_lines(actual_arg_text)
│       └─ 复杂表达式 → trace_go_expr(param_name, actual_arg)
│
└─ 3. 返回第一个可信结果
```

### 7.2 跨文件搜索优先级

```
_trace_variable_in_lines_impl 中发现 var_name 是形参
│
├─ 1. 当前文件调用点搜索
│   └─ _trace_param_at_call_sites_ast(file_path, tree)
│
├─ 2. import_map 精确跨文件搜索
│   ├─ _parse_go_imports(file_path) → candidate_files
│   ├─ 去重（seen 集合）
│   └─ for other_fp in unique_candidates:
│       └─ _trace_param_at_call_sites_ast(other_fp, other_tree)
│
└─ 3. 暴力搜索 fallback
    └─ for other_fp in pre_result (language='go', not in seen):
        └─ _trace_param_at_call_sites_ast(other_fp, other_tree)
```

---

## 八、分支约束追踪

### 8.1 BranchConstraint 集成

Go 引擎复用了共享模块的 `BranchConstraint` 类，在 `_ast_trace.py` 中实现 Go 特定的约束提取。

### 8.2 extract_constraints_from_go_expr

```python
def extract_constraints_from_go_expr(expr_node):
    """
    从 Go if 条件表达式中提取 BranchConstraint 列表。
    
    支持的模式：
    - x == value       → BranchConstraint(x, '==', value)
    - x != nil         → BranchConstraint(x, '!=', None)
    - x != ""          → BranchConstraint(x, '!=', "")
    - len(x) > 0       → BranchConstraint(x, '>', 0)
    - x && y           → 分别提取左右
    - x || y           → 收集同一变量的枚举约束 → BranchConstraint(x, 'in', [a, b])
    - !expr            → 取反内部约束
    """
```

**操作符分类：**
- **比较运算**：`==`, `!=`, `>=`, `<=`, `>`, `<` → 直接提取约束
- **逻辑 AND**：`&&` → 递归分别提取（Go tree-sitter 将 `&&` 映射为 `binary_expression`）
- **逻辑 OR**：`||` → 收集同一变量的 `==` 值，合并为 `in` 约束
- **逻辑 NOT**：`!` → 对内部约束取反（`negate()`）

### 8.3 if 语句分支约束

```python
# trace_go_stmt 中处理 if_statement：
if_expr_node = ...  # 提取条件表达式节点
go_constraints = extract_constraints_from_go_expr(if_expr_node)
sink_branch = _find_sink_branch_go(stmt_node, vul_lineno)

if sink_branch == 'if':
    # sink 在 if 体中 → 原始约束阻断
    for c in go_constraints:
        if c.var_name == var_name and c.op in ('==', '===', 'in'):
            return (-1, 0)  # 被约束阻断

elif sink_branch == 'else':
    # sink 在 else 体中 → 取反约束阻断
    else_constraints = [c.negate() for c in go_constraints]
    for c in else_constraints:
        if c.var_name == var_name and c.op in ('==', '===', 'in'):
            return (-1, 0)  # 被取反约束阻断

else:
    # sink 在 if 语句外部 → 遍历所有分支
    ...
```

### 8.4 for 语句（while 形式）约束

Go 没有 while 关键字，`for condition {}` 等价于 while：

```python
# 检测 while 形式：有 condition 但没有 init/update（无 ';'）
_is_while_form = True
for child in for_node.children:
    if child.type == ';':
        _is_while_form = False  # 有 init 或 update，不是纯 while

if _is_while_form and sink 在 for 体内:
    constraints = extract_constraints_from_go_expr(condition)
    for c in constraints:
        if c.var_name == var_name and c.op in ('==', '===', 'in'):
            return (-1, 0)  # while 条件约束阻断
```

### 8.5 switch 语句约束

```python
# sink 在非 default case 中 → 阻断
# 推理：switch expr == case_value，所以 sink 分支有等值约束
if sink_in_case and not sink_case_is_default:
    return (-1, None, 0)  # 约束阻断

# sink 在 default case 或不在 switch 中 → 搜索赋值并回溯
```

---

## 九、RHS 分析分派器

### 9.1 _analyze_rhs_node

`_analyze_rhs_node` 是 `parser.py` 中的 RHS 分析分派器，按 AST 节点类型分派：

```
_analyze_rhs_node(rhs_node, var_name, file_path, lineno, to_line)
│
├─ 快速检查：_is_controllable_source → (1, lineno)
├─ 快速检查：_is_repair_function → (2, lineno)
├─ 字面量 → (-1, 0)
├─ call_expression → _handle_call_expression_rhs
├─ binary_expression → _handle_binary_expression_rhs
├─ identifier → 递归追踪或可控检查
├─ selector_expression → 基础变量可控检查
├─ parenthesized_expression → 解包递归
├─ type_conversion_expression → 递归追踪参数
└─ 其他 → 收集标识符逐一追踪
```

### 9.2 _handle_call_expression_rhs

```python
def _handle_call_expression_rhs(call_node, var_name, ...):
    func_text = _get_call_func_text(call_node)
    
    # 1. 内置知识库 → safe → (-1, 0)
    # 2. passthrough/param_flow → 追踪 ALL 非字面量参数
    #    ⚠️ 关键修复：不只追踪 passthrough 索引，追踪所有参数
    # 3. 未知函数 → function_back_go deps 追踪
    #    ├─ code='deps' → 逐个追踪 caller_deps
    #    ├─ code=1/2 → 直接返回
    #    └─ code=3 → (3, lineno)
```

---

## 十、函数定义索引与预构建

### 10.1 _build_func_def_index

```python
def _build_func_def_index(file_path):
    """
    预扫描文件中的 func 定义，建立索引。
    使用正则匹配 `func (receiver) Name(params)` 模式。
    """
    if _func_def_index_built.get(file_path):
        return
    
    for line in lines:
        m = re.match(r'func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(', line)
        if m:
            func_name = m.group(1)
            _func_def_index[(file_path, func_name)] = (formal_params, body_lines, def_lineno)
```

### 10.2 _find_function_def_in_lines

```python
def _find_function_def_in_lines(lines, func_name, vul_lineno):
    """
    在文件行列表中查找函数定义。
    处理多种格式：
    - func Name(params) return_type { ... }
    - func (receiver *Type) Name(params) { ... }
    """
```

---

## 十一、analysis_params（CAST 跨文件分析接口）

```python
def analysis_params(param_name, parent_func_names, vul_function, lineno, file_path,
                    repair_functions=None, controlled_params=None, isexternal=False):
    """
    Go 变量可控性分析（供 CAST 跨文件分析调用）。
    
    返回: (is_controllable, controlled_params, expr_lineno, chain)
    """
    # 预建索引 → 追踪变量 → 编码结果
```

这是 CAST（Cross-file AST Tracing）系统的接口函数，供其他引擎或全局分析器调用。Go 引擎的实现相对简单，直接调用 `_trace_variable_in_lines` 并转换结果格式。

---

## 十二、完整数据流图

### 12.1 从 Sink 到 Source 的完整追踪链路

以一个具体的 Go 命令注入为例：

```go
// main.go
package main

import "os/exec"

func runCmd(userInput string) error {
    cmd := exec.Command("sh", "-c", userInput)  // Line 10: sink
    return cmd.Run()
}

func handler(c *gin.Context) {
    input := c.Query("cmd")    // Line 15: source (gin框架)
    runCmd(input)              // Line 16: caller
}
```

**追踪链路：**

```
scan_parser(["exec.Command"], 10, "main.go")
│
├─ _find_call_at_line → call_node = exec.Command("sh", "-c", userInput)
├─ _get_call_args_from_ast → [arg0="sh", arg1="-c", arg2=identifier("userInput")]
│
├─ 对 arg2 (userInput):
│   ├─ _collect_identifiers → ["userInput"]
│   └─ _trace_variable_in_lines("main.go", "userInput", 10)
│       │
│       ├─ _trace_variable_in_lines_impl:
│       │   ├─ _parse_go_ast("main.go")
│       │   ├─ _find_enclosing_function → "runCmd"
│       │   ├─ 反向遍历 statement_list:
│       │   │   └─ stmt: short_var_declaration(cmd := exec.Command(...))
│       │   │       → cmd ≠ userInput → 跳过
│       │   │
│       │   ├─ 未找到赋值 → 检查形参
│       │   │   └─ _get_formal_param_names → ["userInput"] ∈ params!
│       │   │
│       │   └─ _trace_param_at_call_sites_ast("runCmd", "userInput", ...)
│       │       ├─ walk AST 找 call_expression(func_name contains "runCmd")
│       │       ├─ 找到: runCmd(input) @ Line 16
│       │       ├─ 形参 ["userInput"], param_idx=0
│       │       ├─ 实参[0] = identifier("input")
│       │       └─ _trace_variable_in_lines("main.go", "input", 16)
│       │           │
│       │           └─ _trace_variable_in_lines_impl:
│       │               ├─ _find_enclosing_function → "handler"
│       │               ├─ 反向遍历 statement_list:
│       │               │   └─ stmt: short_var_declaration(input := c.Query("cmd"))
│       │               │       ├─ _check_assignment_node → lhs="input", rhs=call_expression
│       │               │       └─ trace_go_expr("input", rhs_node)
│       │               │           └─ rhs is call_expression → _trace_call_expr
│       │               │               ├─ func_name = "c.Query"
│       │               │               ├─ lookup_builtin("c.Query")
│       │               │               │   └─ passthrough: [0] → 追踪参数[0]
│       │               │               ├─ arg_node = interpreted_string_literal("cmd")
│       │               │               │   └─ _is_literal_node_safe → 跳过
│       │               │               └─ 但 c.Query 本身是可控源！
│       │               │                   └─ _is_controlled_source_node → "c.Query" ∈ GO_CONTROLLED_SOURCES
│       │               │                       └─ return (1, 15)  ✅
│       │               └─ return (1, 15)
│       │
│       └─ return (1, 15)
│
└─ return (1, 15) → code=1, 漏洞成立
    chain: [('source', 'input', 'main.go', 15), ('sink', 'exec.Command', 'main.go', 10)]
```

### 12.2 跨函数 sink 内联追踪

以一个跨函数的例子：

```go
func dangerous(param string) {
    exec.Command("sh", "-c", param)  // Line 20: sink
}

func handler(c *gin.Context) {
    input := c.Query("cmd")    // Line 25: source
    dangerous(input)           // Line 26
}
```

**追踪链路：**

```
scan_parser(["exec.Command"], 20, "file.go")
│
├─ AST 提取 → arg[0]=identifier("param")
├─ _trace_variable_in_lines("param", 20)
│   └─ 找到函数体 → param 是形参
│       └─ _trace_param_at_call_sites_ast("dangerous", "param")
│           ├─ 找到调用点: dangerous(input) @ Line 26
│           ├─ 实参[0] = "input"
│           └─ _trace_variable_in_lines("input", 26)
│               └─ ... → (1, 25)
│
└─ 或者，另一种路径：
    function_back_go("dangerous", "input", 26, ...)
    ├─ _trace_callee_body_for_sinks(...)
    │   ├─ 解析 callee → 找到 exec.Command sink
    │   ├─ arg_map: {param: "input"}
    │   ├─ sink 参数 identifier("param") ∈ arg_map
    │   └─ arg_map["param"] = "input"
    │       └─ _is_controllable_source("input") → False
    │           └─ _extract_var_names_from_expr("input") → ["input"]
    │               └─ return ('deps', ['input'])
    │
    └─ 回到 caller → _trace_variable_in_lines("input", ...)
        └─ (1, 25)
```

---

## 十三、Go 引擎设计特点总结

### 13.1 与其他引擎的差异

| 特性 | Go | PHP | JS | Python | Java | C/C++ |
|------|-----|-----|-----|---------|------|-------|
| 解析器 | tree-sitter | lphply | lesprima | builtins ast | ljavalang | lesprima |
| AST 缓存 | ✅ 模块级 | ❌ | ❌ | ❌ | ❌ | ❌ |
| 函数定义索引 | ✅ 预构建 | ❌ | ❌ | ❌ | ❌ | ❌ |
| import 跨文件 | ✅ import_map | ❌ | ❌ | ❌ | ❌ | ❌ |
| 纯 AST 追踪 | ✅ _ast_trace.py | ❌ 混合 | ❌ 混合 | ✅ ast 模块 | ❌ 混合 | ❌ 混合 |
| Callee sink 检查 | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| 形参→实参映射 | ✅ AST | ✅ 正则 | ✅ 正则 | ✅ AST | ✅ 正则 | ✅ 正则 |

### 13.2 Go 引擎独特设计

1. **tree-sitter 双文件架构**：parser.py（回溯主控）+ _ast_trace.py（纯 AST 追踪），职责分离清晰
2. **import_map 精确跨文件**：Go 的包系统天然支持 import 路径→文件映射，这是其他引擎不具备的
3. **函数定义预构建索引**：`_func_def_index` 避免每次调用都正则扫描全文
4. **四层缓存体系**：AST、import、包名、函数定义，极大减少重复解析
5. **callee body sink 检查**：先检查 callee 内是否有 sink，再 fallback 到返回值分析
6. **双轨追踪**：AST 追踪为主路径，文本追踪为 fallback，确保兼容性
7. **递归防护栈**：`_scan_function_stack` 防止递归函数导致无限循环

### 13.3 潜在改进方向

1. **AST 缓存无失效机制**：文件修改后缓存不会自动失效
2. **暴力搜索 fallback 性能**：当 import_map 未覆盖时，遍历所有 Go 文件
3. **多返回值处理简化**：当前只取第一个返回值，可能遗漏多返回值场景
4. **interface 类型不支持**：Go 的 interface 使得静态类型分析受限
5. **goroutine 不追踪**：`go func()` 启动的协程不追踪
