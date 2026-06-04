# Java 引擎回溯分析设计文档

> **模块路径**: `core/core_engine/java/`
> **核心文件**: `parser.py` (2165行)
> **辅助文件**: `builtin_knowledge.py`, `summary_generator.py`
> **解析器**: `ljavalang` (Kunlun-M 自研，PyPI: ljavalang>=2.0.2,<3)

---

## 1. 解析器选型与技术架构

### 1.1 为什么自研 ljavalang

Java 有多个 Python 可用的解析器（javalang, python-javatrans, PyJava 等），Kunlun-M 选择自研 `ljavalang` 的理由：

| 因素 | ljavalang | javalang (开源) |
|------|-----------|----------------|
| 维护权 | 项目可控，可随时修 bug | 第三方，PR 响应慢 |
| 链式调用处理 | `_flatten_chained_calls` 适配 | selectors 结构不够直观 |
| 与 pretreatment 集成 | 统一 AST 缓存格式 | 需要适配层 |
| 行号精度 | `position` 属性精确 | 一致 |

**已知局限**: ljavalang 在处理复杂链式调用（如 `Base64.getDecoder().decode(data)`）时 AST 可能丢失节点。Java 引擎专门为此设计了**源码文本 fallback** 机制。

### 1.2 全局状态设计

```python
# Line 13-22
scan_results = []          # 当前扫描结果
is_repair_functions = []   # 修复函数列表
is_controlled_params = []  # 可控参数列表
scan_chain = []            # 调用链

_trace_cache = TraceCache("java")           # 双层缓存
_summaries_initialized = False                # 摘要初始化标志
_file_summaries = {}                          # 文件级摘要缓存
_scan_function_stack = []                     # 函数追踪栈（防递归）
```

**关键差异**: Java 引擎额外维护 `_scan_function_stack`（函数调用栈）和 `_file_summaries`（带磁盘缓存的文件摘要），这两者是 Java 引擎独有的。

---

## 2. 核心回溯函数链路

### 2.1 返回码体系

Java 引擎使用与 Go/Python/JS 统一的简化返回码：

| Code | 含义 | 处理策略 |
|------|------|---------|
| `1` | **可控** | 漏洞确认 |
| `2` | **已修复** | 经过修复函数处理 |
| `3` | **未确认** | 继续追踪 |
| `-1` | **不可控** | 分支约束阻断或污点断裂 |
| `'deps'` | **依赖调用者变量** | 与 Python 引擎一致的 deps 机制 |

**注意**: Java 引擎**没有 code=4/5**（不像 Python 引擎有"新漏洞函数"和"global 变量"）。这是因为 Java 的 OOP 模型下，跨方法传播通过 `_propagate_controllable_across_calls` 和 `_check_caller_controllability` 预处理完成，不需要在回溯链路中动态处理 code=4。

### 2.2 入口函数: `scan_parser`

**位置**: Line 1962-2165

Java 引擎的 `scan_parser` 采用**反向追踪模式**（与 Go/Python/PHP/JS 统一）。完整流程：

```
scan_parser(sensitive_func, vul_lineno, file_path, ...)
  │
  ├─ 1. 重置全局状态 (cache, summaries, stack)
  ├─ 2. 初始化函数摘要 (_init_function_summaries)
  ├─ 3. 找到包含目标行号的方法 (_find_method_at_line)
  ├─ 4. 读取源码行（文本 fallback 用）
  ├─ 5. 搜索 sink：
  │     ├─ 5a. MethodInvocation 搜索（_flatten_chained_calls 展开）
  │     │     ├─ 对每个参数: parameters_back
  │     │     └─ code=-1/1/2/'deps' → 写入 scan_results
  │     │
  │     ├─ 5b. ClassCreator 搜索（构造函数调用如 new FileInputStream(...)）
  │     │     └─ 同上
  │     │
  │     └─ 5c. 源码文本 fallback（javalang AST 丢失时）
  │           └─ regex 匹配 → 提取参数名 → parameters_back
  │
  └─ 6. return scan_results
```

**三层搜索设计** (5a → 5b → 5c):

这是 Java 引擎的**容错设计**。由于 ljavalang 在复杂链式调用下可能丢失 AST 节点，当 5a 和 5b 都找不到 sink 时，5c 使用 regex 在源码中搜索（最多向后看 15 行），作为最后的兜底手段。

### 2.3 核心追踪: `parameters_back`

**位置**: Line 365-587

```python
def parameters_back(param_name, stmts, vul_lineno, file_path,
                     repair_functions=None, controlled_params=None,
                     depth=0, max_depth=10):
```

**函数签名特点**: `stmts` 参数是方法体的语句列表（从 pretreatment 获取的 AST 节点）。与 Python 引擎不同，Java 引擎**不使用** `ast_object_singleton.get_nodes()`，而是在 `scan_parser` 中通过 `_find_method_at_line` 获取方法节点，然后传入 `method.body` 作为 `stmts`。

**执行流程**:

```
parameters_back(param_name, stmts, vul_lineno, ...)
  │
  ├─ 深度检查: depth > max_depth(10) → return (3, None, 0)
  ├─ 缓存查询: _trace_cache.get(file_path, param_name, vul_lineno)
  ├─ 直接可控检查: param_name in controlled_params
  │
  ├─ 倒序遍历 stmts（从 sink 行向上）
  │     │
  │     ├─ LocalVariableDeclaration: Type varName = expr
  │     │     └─ 匹配 varName → _trace_expr(initializer, ...)
  │     │
  │     ├─ StatementExpression + Assignment: varName = expr
  │     │     └─ 匹配 target_name → _trace_expr(value, ...)
  │     │
  │     ├─ IfStatement → 分支约束分析（详见第3节）
  │     │
  │     ├─ WhileStatement / DoStatement → 条件约束 + 体内递归
  │     │
  │     ├─ ForStatement → 体内递归
  │     │
  │     ├─ TryStatement → block + catches 递归
  │     │
  │     └─ SwitchStatement → 分支约束分析（详见第3节）
  │
  └─ 未找到赋值 → return (-1, None, 0) + 写入缓存
```

**缓存策略**: Java 引擎在**每次找到赋值后立即缓存结果**（无论返回什么 code），这与 Python 引擎只缓存确定性结果不同。这使得 Java 引擎在多分支场景下的缓存命中率更高。

### 2.4 表达式级追踪: `_trace_expr`

**位置**: Line 590-684

```
_trace_expr(expr, stmts, lineno, ...)
  │
  ├─ Literal → return (-1, None, 0)
  │
  ├─ MemberReference (变量引用)
  │     ├─ is_controllable_source → return (1, ...)
  │     └─ parameters_back(var_name, ...)
  │
  ├─ MethodInvocation → function_back_java
  │
  ├─ BinaryOperation → 左右分别追踪
  │     ├─ 任一侧 code=1 → return code=1
  │     └─ 两侧 deps → 合并 deps 列表
  │
  ├─ Cast (类型转换) → _trace_expr(inner)
  ├─ Assignment → _trace_expr(value)
  ├─ ClassCreator → 追踪构造参数
  │
  └─ TernaryExpression → 三元约束分析
```

**deps 合并机制** (Line 629-635):

```python
deps = []
if left_result[0] == 'deps':
    deps.extend(left_result[1] if isinstance(left_result[1], list) else [left_result[1]])
if right_result[0] == 'deps':
    deps.extend(right_result[1] if isinstance(right_result[1], list) else [right_result[1]])
if deps:
    return ('deps', list(set(deps)), lineno)
```

二元运算两侧都是 deps 时，合并去重返回。这是 `'deps'` 机制的核心——它**不在当前作用域内解析**，而是将依赖变量名传递给上层调用者继续追踪。

### 2.5 函数调用追踪: `function_back_java`

**位置**: Line 713-810

`function_back_java` 是 Java 引擎中最复杂的单函数，实现了**6 级优先级判定**：

```
function_back_java(call_node, stmts, ...)
  │
  ├─ 递归检查: full_name in _scan_function_stack → return (-1, None, 0)
  │
  ├─ 1. request source 检查
  │     └─ _is_request_source("getParameter"/"getHeader"/...) → return (1, ...)
  │
  ├─ 2. 内置知识库查询
  │     ├─ safe + no passthrough → return (-1, None, 0)
  │     └─ passthrough → 追踪对应位置参数
  │
  ├─ 3. 修复函数检查
  │     └─ _has_repair_function → return (2, ...)
  │
  ├─ 4. 函数摘要判定
  │     └─ _judge_from_summary_java(callee_summary, call_node, ...)
  │
  ├─ 5. AST 函数体分析
  │     ├─ _build_global_method_map → 跨文件查找方法定义
  │     ├─ 遍历 ReturnStatement
  │     ├─ 建立形参→实参映射
  │     └─ _trace_return_in_func(return_expr, func_body, func_params, call_args, ...)
  │
  └─ 6. 参数级追踪（fallback）
        └─ 逐参数 _trace_expr → 任意可控即 return (1, ...)
```

**递归保护** (Line 732-734):

```python
_scan_function_stack.append(full_name)
try:
    # ... AST 分析 ...
finally:
    if full_name in _scan_function_stack:
        _scan_function_stack.remove(full_name)
```

使用 `try/finally` 确保即使异常也能正确清理栈。这避免了 `A() 调用 B() → B() 内 return A()` 的无限递归。

### 2.6 函数体内返回值追踪: `_trace_return_in_func`

**位置**: Line 813-852

当 `function_back_java` 进入第 5 步（AST 函数体分析）时，对每个 `return` 语句的表达式进行追踪：

```python
def _trace_return_in_func(expr, func_body_stmts, func_params, call_args, ...)
    │
    ├─ MemberReference → 检查是否是形参
    │     ├─ 是 → 参数映射: func_params[i] → call_args[i] → _trace_expr(call_arg, ...)
    │     └─ 否 → 在函数体内 parameters_back
    │
    ├─ MethodInvocation → _is_request_source → return (1, ...)
    │
    └─ BinaryOperation → 左右分别 _trace_return_in_func
```

**关键设计 — 参数映射**:

当 return 语句引用形参 `s` 时，需要找到调用者传入的实参 `request.getParameter("cmd")`：

```
// 调用点
String result = doSomething(request.getParameter("cmd"));

// 被调用函数
String doSomething(String s) {
    return "ls " + s;  // return 表达式中 s 是形参
}
```

`_trace_return_in_func` 发现 `s` 在 `func_params` 中，映射到 `call_args[0]`（即 `request.getParameter("cmd")`），然后 `_trace_expr(call_args[0], [])` 在调用者上下文中追踪。

---

## 3. 分支约束分析

### 3.1 if/else if/else — `_find_sink_branch_java`

**位置**: Line 889-914

```python
def _find_sink_branch_java(if_stmt, vul_lineno):
    # then 体范围检查
    if then_line <= vul_lineno <= then_end:
        return 'if'
    # else if 递归
    if isinstance(else_statement, IfStatement):
        return _find_sink_branch_java(else_statement, vul_lineno)
    # else 体范围检查
    if else_line <= vul_lineno <= else_end:
        return 'else'
    return 'outside'
```

**约束提取与阻断** (在 `parameters_back` 中，Line 428-498):

```python
if sink_branch == 'if':
    constraints = extract_constraints_from_java_expr(stmt.condition)
    for c in constraints:
        if c.var_name == param_name and c.op in ('==', '===', 'in'):
            return (-1, None, 0)  # 阻断

elif sink_branch == 'else':
    else_constraints = [c.negate() for c in java_constraints]
    # else if: 递归处理
    # else: 检查取反约束
```

**outside 分支的处理** (Line 476-498):

当 sink 不在 if/else 的任何分支体内（outside）时，Java 引擎的策略是**遍历所有分支找重赋值**。如果 then 分支中有 `x = "fixed"`，则 `x` 被重新赋值为不可控值，覆盖之前的可控源。

### 3.2 条件表达式解析 — `extract_constraints_from_java_expr`

**位置**: Line 242-320

| Java 语法 | AST 节点 | 提取结果 |
|-----------|---------|---------|
| `x == value` | `BinaryOperation(==)` | `BranchConstraint(var=x, op='==', value)` |
| `x != value` | `BinaryOperation(!=)` | `BranchConstraint(var=x, op='!=', value)` |
| `x && y` | `BinaryOperation(&&)` | 递归合并两个子约束 |
| `x \|\| y` | `BinaryOperation(\|\|)` | OR 优化 → `in` 约束 |
| `x.equals(y)` | `MethodInvocation(equals)` | `BranchConstraint(var=x, op='==', value=y)` |
| `"test".equals(x)` | 反向 equals | 变量名从 argument 提取 |
| `!x.equals(y)` | prefix_operators 含 `!` | `negate()` 取反 |

**OR 优化** (Line 269-285):

```python
# x.equals("a") || x.equals("b") → BranchConstraint(var=x, op='in', value=["a","b"])
eq_values = defaultdict(list)
for c in or_constraints:
    if c.op == '==' and c.var_name:
        eq_values[c.var_name].append(c.value)
for var_name, values in eq_values.items():
    result.append(BranchConstraint(var_name=var_name, op='in', value=values))
```

**"常量.equals(变量)" 模式** (Line 306-310):

Java 最佳实践推荐 `"constant".equals(variable)` 避免 NPE。Java 引擎专门处理这种反向写法：

```python
if not obj and isinstance(expr.qualifier, Literal):
    obj = _get_java_expr_name(expr.arguments[0])   # 从 argument 提取变量名
    value = _get_java_literal(expr.qualifier)       # 从 qualifier 提取字面量
```

### 3.3 switch/case 约束

**位置**: Line 540-583

```python
# 判断 sink 在哪个 case
if sink_in_case:
    # sink 在非 default case → switch(expr) == case_value → 阻断
    return (-1, None, 0)

# default case 或 sink 不在 case 中 → 遍历目标 case 内的语句
for case in stmt.cases:
    if first_line <= target_line <= last_line:
        result = parameters_back(param_name, case_stmts, ...)
        if result[0] in (1, 2):
            return result
        # case 内未找到 → break 外层 for，继续搜索 switch 之前的 stmts
        break
```

**设计语义**: Java switch 语句中，进入非 default case 意味着 `switch(expr)` 的值等于 case 常量。如果追踪的变量就是 switch 表达式，则在 case 内它被约束为固定值，不可控。

**fallthrough 处理**: 如果目标 case 内找不到赋值，不直接返回 `-1`，而是 `break` 出内层循环，让外层 `for stmt in reversed(stmts)` 继续搜索 switch 之前的语句。这正确处理了 fallthrough 场景。

### 3.4 while 循环约束

**位置**: Line 500-519

```python
if body_start <= _vul_line <= body_end:
    constraints = extract_constraints_from_java_expr(stmt.condition)
    for c in constraints:
        if c.var_name == param_name and c.op in ('==', '===', 'in'):
            return (-1, None, 0)  # while (x == "fixed") → 死循环，sink 不可达
```

### 3.5 三元表达式约束

**位置**: Line 657-682

```python
if isinstance(expr, javalang.tree.TernaryExpression):
    true_refs = _collect_member_references(expr.if_true)
    false_refs = _collect_member_references(expr.if_false)
    constraints = extract_constraints_from_java_expr(expr.condition)

    # 约束变量只在 true 分支 → true 路径中 var == fixed → 阻断
    if c.var_name in true_refs and c.var_name not in false_refs:
        return (-1, None, 0)
    # 约束变量只在 false 分支 → 追踪 false 分支
    elif c.var_name in false_refs and c.var_name not in true_refs:
        return _trace_expr(expr.if_false, ...)
```

---

## 4. Java 特有的可控源识别系统

### 4.1 框架感知的可控变量收集

Java 引擎与 PHP/JS/Python 的最大差异在于：Java **没有全局超全局变量**，可控源完全依赖框架（Servlet API / Spring / JAX-RS）。因此 Java 引擎实现了**框架感知的可控变量收集器** `_collect_controllable_vars`。

**位置**: Line 1031-1128

```
_collect_controllable_vars(method_node, request_var_names, source_lines)
  │
  ├─ 1. request 变量本身可控
  │     └─ request_var_names → controllable
  │
  ├─ 2. 方法参数识别（基于类型和注解）
  │     ├─ HttpServletRequest 类型 → 可控 (Servlet API)
  │     ├─ MultipartFile / InputStream 类型 → 可控 (文件上传)
  │     ├─ Principal 类型 → 可控 (认证)
  │     └─ 注解标记 → 可控
  │           ├─ Spring: @RequestParam, @PathVariable, @RequestBody, ...
  │           └─ JAX-RS: @PathParam, @QueryParam, @FormParam, ...
  │
  ├─ 3. 局部变量追踪
  │     ├─ request.getParameter/getHeader/... → 可控
  │     └─ controllable.map.get("key") → 可控 (间接传播)
  │
  └─ 4. 对象级污点传播 (_propagate_object_taint)
```

**Spring 注解识别** (Line 1082-1092):

```python
SPRING_PARAM_ANNOTATIONS = {
    'RequestParam', 'PathVariable', 'RequestBody',
    'RequestHeader', 'CookieValue', 'ModelAttribute',
}
JAXRS_PARAM_ANNOTATIONS = {
    'PathParam', 'QueryParam', 'FormParam',
    'HeaderParam', 'BeanParam',
}
```

对于带全限定名的注解（如 `org.springframework.web.bind.annotation.RequestParam`），自动取最后一部分匹配。

### 4.2 `_REQUEST_SOURCE_METHODS` 硬编码列表

**位置**: Line 689-694

```python
_REQUEST_SOURCE_METHODS = frozenset({
    "getParameter", "getHeader", "getInputStream", "getReader",
    "getQueryString", "getCookies", "getParameterValues", "getParameterMap",
    "getProtocol", "getScheme", "getServerName", "getRemoteAddr",
    "getPart", "getParts", "getInputStream",
})
```

这是 Java Servlet API 的标准输入获取方法。`_is_request_source` 使用 `frozenset` 确保 O(1) 查找性能。

---

## 5. 跨文件与跨方法传播

Java 引擎实现了 Kunlun-M 中**最复杂**的跨文件传播系统，分为三个层级。

### 5.1 第一层: 对象级污点传播 — `_propagate_object_taint`

**位置**: Line 1131-1254

在**方法内部**，通过多轮迭代传播标记所有间接可控的变量：

| 模式 | 代码示例 | 传播逻辑 |
|------|---------|---------|
| A: 构造函数 | `URL url = new URL(userInput)` | 构造参数可控 → 对象可控 |
| B1: 方法参数 | `Object o = deserialize(data)` | 方法参数可控 + 透传 → 结果可控 |
| B2: qualifier | `conn = url.openConnection()` | 调用对象可控 → 结果可控 |
| B3: 链式 selectors | `result = a.b().c()` | 中间结果可控 → 最终结果可控 |
| C: 字符串拼接 | `query = "SELECT " + input` | 任一操作数可控 → 结果可控 |
| D: 类型转换 | `String s = (String) obj` | 被转换对象可控 → 结果可控 |
| E: 简单赋值 | `String s = input` | 源可控 → 目标可控 |

**多轮迭代** (Line 1145-1147):

```python
while changed and rounds < max_rounds:  # max_rounds=5
    changed = False
    rounds += 1
```

传播不是单轮的——第一轮标记 `x` 可控后，第二轮才能发现 `y = x + "suffix"` 也可控。

**源码文本 fallback** (Line 1233-1254):

这是针对 ljavalang 解析失败的特殊处理：

```python
# 去掉字符串字面量中的匹配
code_only = re.sub(r'"[^"]*"', '""', line_text)
code_only = re.sub(r"'[^']*'", "''", code_only)
# 检查剩余文本中是否包含可控变量名（单词边界匹配）
for var in list(controllable):
    if re.search(r'\b' + re.escape(var) + r'\b', code_only):
        controllable.add(declarator.name)
```

**设计意图**: 当 `Base64.getDecoder().decode(data)` 这样的链式调用被 ljavalang 错误解析时，AST 中可能丢失节点。此时用源码文本做最后的兜底传播。

### 5.2 第二层: 跨方法透传传播 — `_propagate_controllable_across_calls`

**位置**: Line 1592-1724

在 `_collect_controllable_vars` 之后调用，用于**跨方法追踪**可控变量的传播：

```
_propagate_controllable_across_calls(method_node, tree, controllable, ...)
  │
  ├─ 构建同文件方法映射: class_methods = _build_class_method_map(tree)
  │
  ├─ 多轮迭代 (max_depth=3)
  │     │
  │     ├─ 模式1: String x = someMethod(y) where y is controllable
  │     │     ├─ 同文件: called_method in class_methods
  │     │     │     └─ _is_passthrough_method(called_method, param_name, ...)
  │     │     └─ 跨文件: global_methods[(name, arg_count)]
  │     │           └─ _is_passthrough_method(remote_method, ...)
  │     │
  │     ├─ 模式2: 字符串拼接
  │     ├─ 模式3: 类型转换
  │     └─ 模式4: toString/valueOf/format/String 方法
  │
  └─ return (controllable 被原地修改)
```

**`_is_passthrough_method` — 透传判定** (Line 1291-1390):

这是 Java 引擎中跨方法传播的核心判定函数：

```
_is_passthrough_method(method_node, param_name, repair_functions, ...)
  │
  ├─ 查内置知识库 → 直接返回 True/False
  │
  ├─ 遍历 ReturnStatement:
  │     ├─ 直接返回参数: return param_name → True
  │     ├─ 参数方法调用: return param_name.trim() → True (qualifier == param_name)
  │     ├─ 嵌套调用: return obj.method(param_name.trim())
  │     │     ├─ 同文件递归: 找到 obj.method → 检查其是否透传
  │     │     └─ 跨文件递归: global_methods → 同上
  │     └─ 修复函数调用 → False
  │
  └─ return False
```

**嵌套透传递归** (Line 1351-1388):

```python
# return sanitize(s.trim())
# → s 传给 trim() → trim 是透传方法
# → trim() 的结果传给 sanitize() → sanitize 是修复函数 → False
```

支持三层嵌套：`obj.method(param.trim())` → 检查 `obj.method` 是否透传 → 检查其第一个参数是否透传 → `trim()` 是透传 → 最终判定取决于 `obj.method`。

### 5.3 第三层: 反向调用链分析 — `_check_caller_controllability`

**位置**: Line 1466-1590

这是 Java 引擎**独有的**功能——当当前方法中没有直接可控源时，**反向查找调用者**，检查调用者是否传入了可控参数：

```
_check_caller_controllability(current_method, ast_obj, repair_functions, ...)
  │
  ├─ 缓存查询: _trace_cache.get("__java_caller__", method_name, depth)
  │
  ├─ 遍历所有 Java 文件的所有方法声明
  │     └─ 查找方法体中是否调用了 current_method_name
  │           ├─ LocalVariableDeclaration 中的调用
  │           ├─ ReturnStatement 中的调用
  │           └─ StatementExpression 中的调用（void 方法）
  │
  ├─ 找到调用！分析调用者
  │     ├─ _find_request_var_names(caller_method)
  │     ├─ _collect_controllable_vars(caller_method, request_vars)
  │     ├─ _propagate_controllable_across_calls(caller_method, ...)
  │     │
  │     ├─ 调用者也没有可控变量？
  │     │     └─ 递归: _check_caller_controllability(caller_method, depth+1)
  │     │
  │     └─ 检查调用参数是否可控
  │           └─ set(refs) & caller_controllable → 找到可控源
  │
  └─ return controllable_params
```

**使用场景**:

```java
// Service.java — 没有 request source
public void execute(String command) {
    Runtime.getRuntime().exec(command);  // sink
}

// Controller.java — 有 request source
public void handle(HttpServletRequest request) {
    String cmd = request.getParameter("cmd");
    service.execute(cmd);  // 传入了可控参数
```

当扫描 `Service.execute()` 时，方法内没有 request source。`_check_caller_controllability` 找到 `Controller.handle()` 调用了 `execute(request.getParameter("cmd"))`，判定 `command` 参数可控。

### 5.4 全局方法映射 — `_build_global_method_map`

**位置**: Line 1401-1437

```python
def _build_global_method_map(ast_obj, current_filepath):
    """返回: {(method_name, param_count): [(tree, method_node, filepath), ...]}"""
```

遍历所有 Java 文件的 AST，构建**跨文件**的方法索引。用 `(method_name, param_count)` 做键来消歧义（Java 允许方法重载）。

---

## 6. 配置类漏洞检测 — `is_config_vuln`

**位置**: Line 1804-1836 (在 `_analyze_call` 中)

Java 引擎独有地支持**配置类漏洞**的检测。这类漏洞不依赖外部输入，而是由固定的危险配置引发：

```java
// Fastjson 反序列化漏洞
ObjectMapper mapper = new ObjectMapper();
mapper.enableDefaultTyping(ObjectMapper.DefaultTyping.NON_FINAL);  // 危险配置

// Shiro 硬编码密钥
new DefaultHashService().setHashAlgorithmName("MD5");  // 不安全算法
```

**判定逻辑**:

```python
if is_config_vuln:
    # 字面量参数为 "true" → 不安全配置
    if not param_var_refs and literal_values:
        for lit in literal_values:
            if lit.lower() == 'true':
                return {"code": 4, ...}  # 配置漏洞

    # 枚举/常量参数但无可控变量 → 固定配置调用
    if param_var_refs and not (set(param_var_refs) & controllable):
        return {"code": 4, ...}  # 配置漏洞
```

`code=4` 是 Java 引擎的**第 6 种返回码**，仅用于配置类漏洞。

---

## 7. 源码文本 Fallback 机制

### 7.1 AST 级 Fallback — `_flatten_chained_calls`

**位置**: Line 38-54

ljavalang 将链式调用 `a.b().c(arg)` 解析为嵌套的 `selectors` 结构，可能导致某些节点丢失。`_flatten_chained_calls` 将其展开为平铺列表：

```python
# a.b().c(arg) →
#   MethodInvocation(member="b", qualifier="a", selectors=[
#       MethodInvocation(member="c", arguments=[arg])
#   ])
# → [原始b节点, c节点]
```

### 7.2 文本级 Fallback — `scan_parser` 第 5c 步

**位置**: Line 2122-2157

当 AST 搜索（5a + 5b）失败时，使用正则表达式在源码中搜索 sink：

```python
for line_offset in range(0, 15):  # 最多向后看 15 行
    pattern = r'(?<!\w)' + re.escape(func_name) + r'\s*\('
    if re.search(pattern, source_line):
        arg_match = re.search(re.escape(func_name) + r'\s*\(\s*([^,)]+)', source_line)
        arg_name = arg_match.group(1).strip()
        code, cp, expr_lineno = parameters_back(arg_name, method_stmts, ...)
```

**设计权衡**: 这种 regex 方法只能提取第一个参数名，不支持复杂表达式。但作为最后的兜底手段，足以覆盖大部分场景。

---

## 8. 完整追踪流程示例

### 示例 1: Spring MVC 直接注入

```java
@GetMapping("/cmd")
public void exec(@RequestParam String cmd) throws IOException {
    Runtime.getRuntime().exec(cmd);  // Line 4 — sink
}
```

```
scan_parser(["exec"], 4, "App.java", ...)
  │
  ├─ _find_method_at_line → exec() 方法
  ├─ _collect_controllable_vars:
  │     ├─ @RequestParam 注解 → cmd 标记为可控
  │     └─ controllable = {"cmd"}
  ├─ 找到 exec() at line 4
  ├─ 参数: cmd
  │     ├─ _collect_member_references → ["cmd"]
  │     └─ set(["cmd"]) & controllable = {"cmd"} → 可控!
  └─ return [{"code": 1, "source": ["cmd"], "chain": ["start", "cmd", "exec"]}]
```

### 示例 2: 跨方法透传 + 反向调用链

```java
// Controller.java
@PostMapping("/rce")
public void handle(@RequestBody String input) {
    service.runCommand(input);     // Line 4
}

// Service.java
public void runCommand(String cmd) {
    Runtime.getRuntime().exec(cmd);  // Line 8 — sink
}
```

```
scan_parser(["exec"], 8, "Service.java", ...)
  │
  ├─ _find_method_at_line → runCommand() in Service.java
  ├─ _collect_controllable_vars:
  │     ├─ cmd 是普通 String 参数，没有注解
  │     └─ controllable = {} (空)
  │
  ├─ 参数: cmd → 不可控
  ├─ _check_caller_controllability(runCommand, ast_obj, ...):
  │     ├─ 遍历所有文件
  │     ├─ 在 Controller.java 的 handle() 中找到 service.runCommand(input)
  │     ├─ _collect_controllable_vars(handle):
  │     │     └─ @RequestBody → input 标记为可控
  │     ├─ 调用参数: input 在 controllable 中
  │     └─ return {"cmd"} (cmd 参数被判定为可控)
  │
  ├─ cmd 现在是可控的
  └─ return [{"code": 1, "source": ["cmd"], ...}]
```

### 示例 3: 分支约束阻断

```java
@GetMapping("/user")
public void getUser(@RequestParam String action, HttpServletResponse resp) {
    String name;
    if ("admin".equals(action)) {
        name = "admin";             // Line 6
        Runtime.getRuntime().exec(name);  // Line 7 — sink
    } else {
        name = action;
    }
}
```

```
scan_parser(["exec"], 7, "App.java", ...)
  │
  ├─ 找到 exec() at line 7
  ├─ 参数: name
  ├─ parameters_back("name", method_stmts, 7, ...):
  │     ├─ 找到 Line 6: name = "admin"
  │     ├─ _trace_expr("admin") → Literal → return (-1, None, 0)
  │     └─ return (-1, None, 0)
  │
  ├─ 但是！还有 if 分支约束分析
  │     ├─ exec() 在 if 体中
  │     ├─ if 条件: "admin".equals(action)
  │     ├─ 提取约束: BranchConstraint(var=action, op='==', value='admin')
  │     └─ 但追踪的变量是 name，不是 action → 不阻断
  │
  └─ name = "admin" 是字面量 → code=-1 → 不可控 ✓
```

### 示例 4: 配置类漏洞

```java
ObjectMapper mapper = new ObjectMapper();
mapper.enableDefaultTyping(    // Line 3 — sink (is_config_vuln=True)
    ObjectMapper.DefaultTyping.NON_FINAL
);
```

```
scan_parser(["enableDefaultTyping"], 3, "Config.java", ..., is_config_vuln=True)
  │
  ├─ 找到 enableDefaultTyping() at line 3
  ├─ 参数: ObjectMapper.DefaultTyping.NON_FINAL
  │     ├─ _collect_member_references → ["NON_FINAL"]
  │     ├─ "NON_FINAL" 不在 controllable 中
  │     ├─ is_config_vuln=True + param_var_refs 存在 + 无可控变量
  │     └─ return {"code": 4, "source": ["NON_FINAL"], ...}  # 配置漏洞
  │
  └─ return [{"code": 4, "source": ["NON_FINAL"], "chain": [...]}]
```

---

## 9. 防护机制

### 9.1 递归深度保护

| 层级 | 限制 | 位置 |
|------|------|------|
| `parameters_back` | `depth > max_depth(10)` | Line 378 |
| `_trace_expr` | `depth > max_depth(10)` | Line 596 |
| `_trace_return_in_func` | `depth > max_depth(10)` | Line 817 |
| `_check_caller_controllability` | `depth >= max_depth(3)` | Line 1479 |
| `_propagate_object_taint` | `rounds < max_rounds(5)` | Line 1147 |
| `_propagate_controllable_across_calls` | `rounds < max_depth(3)` | Line 1615 |
| `_is_passthrough_method` | `depth >= max_depth(3)` | Line 1315 |

**设计哲学**: 内层函数（`parameters_back`/`_trace_expr`）允许较深的递归（10），外层传播函数（调用链分析/跨方法传播）限制较浅（3）。这平衡了分析精度和性能。

### 9.2 函数调用栈保护

```python
_scan_function_stack = []  # Line 22

# function_back_java 中
if full_name in _scan_function_stack:
    return (-1, None, 0)  # 检测到递归调用，终止
```

### 9.3 缓存策略

Java 引擎使用**双层缓存**:

1. **TraceCache** (`_trace_cache`): 存储回溯结果，key = `(file_path, param_name, vul_lineno)`
2. **SummaryCacheManager** (`_file_summaries`): 文件级函数摘要缓存，支持磁盘持久化

Java 引擎比其他引擎**更积极地缓存**——`parameters_back` 在每次找到赋值后立即缓存，不区分确定性/非确定性结果。

### 9.4 方法定位容错

**位置**: Line 1014-1028

```python
# Fallback: grep 10行缓冲可能导致行号偏移，扩大搜索范围
for offset in range(1, 11):
    for direction in (offset, -offset):
        adj_target = target + direction
        if start <= adj_target < upper:
            return method
```

由于 pretreatment 的 grep 匹配可能产生行号偏移（±10行），`_find_method_at_line` 在精确匹配失败后，尝试在 ±10 行范围内查找最近的方法。

---

## 10. 与其他引擎的设计对比

| 特性 | Java | Python | PHP | JavaScript |
|------|------|--------|-----|-----------|
| 解析器 | ljavalang (自研) | 标准库 ast | lphply | lesprima |
| 可控源识别 | 框架注解 + 类型推断 | 规则配置 | 硬编码超全局变量 | 规则配置 |
| 反向调用链 | `_check_caller_controllability` | 无 | 无 | 无 |
| 跨方法传播 | `_is_passthrough_method` + 全局方法索引 | `_resolve_code4` | 内联 | 内联 |
| 对象污点 | `_propagate_object_taint` (5种模式) | `_trace_self_attribute` | `$this` | this + 原型 |
| 配置漏洞 | `is_config_vuln` + code=4 | 无 | 无 | 无 |
| 文本 fallback | regex + 赋值传播 | 无 | 无 | 无 |
| 方法定位容错 | ±10 行偏移搜索 | 无 | 无 | 无 |
| 函数摘要缓存 | SummaryCacheManager (磁盘持久化) | 内存注册表 | 共享 | 共享 |

---

## 11. 已知限制

1. **方法重载不精确**: `_build_global_method_map` 用 `(name, param_count)` 消歧义，但 Java 允许同名同参数数量但类型不同的重载，当前无法区分。

2. **静态方法/字段未追踪**: `static` 字段和方法的跨方法传播未被支持。当前只追踪实例方法和局部变量。

3. **继承链不完整**: `_find_method_at_line` 按文件内方法位置查找，不处理类继承中方法重写/覆盖的情况。

4. **泛型不支持**: `List<String>` 等泛型参数的污点传播不追踪（javalang AST 中泛型信息有限）。

5. **Lambda/Stream 未处理**: Java 8+ 的 Lambda 表达式和 Stream API 中的数据流未被追踪。

6. **反射调用不支持**: `Class.forName()`, `Method.invoke()` 等反射调用无法追踪。

7. **跨文件传播仅一层**: `_propagate_controllable_across_calls` 虽然支持递归，但 `global_methods` 映射只包含已解析的文件，不处理运行时动态加载的类。

8. **_analyze_call 未被实际调用**: `_analyze_call` 函数（Line 1755-1895）实现了完整的参数分析逻辑，包括配置漏洞检测和无参数方法 qualifier 检查。但在当前 `scan_parser` 中，这部分逻辑被 `parameters_back` + `function_back_java` 的组合替代，`_analyze_call` 仅作为备用逻辑保留。
