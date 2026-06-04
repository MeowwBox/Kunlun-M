# PHP 引擎回溯分析设计文档

## 1. 概述

PHP 引擎是 Kunlun-M 中历史最悠久、功能最完善的语言引擎，也是整个框架的"原型引擎"。其设计模式被其他语言引擎所借鉴。PHP 引擎位于 `core/core_engine/php/parser.py`，共 **3241 行**，使用自维护的 [lphply](https://pypi.org/project/lphply/) 解析器（支持 PHP 5.6-8.5）。

### 核心设计哲学

1. **AST 节点遍历 + 反向回溯**：以 `analysis()` 遍历 AST 节点树定位 sink 点，以 `parameters_back()` 反向回溯变量来源
2. **双层架构**：`analysis()` 负责"发现 sink"，`parameters_back()` 负责"判断可控性"
3. **污点替换**：每次找到变量的赋值来源，用新污点替换旧污点，继续向上回溯
4. **全局状态**：使用模块级全局变量（`scan_results`、`scan_chain`、`scan_function_stack`）传递扫描状态

## 2. 解析器选型

| 项目 | 说明 |
|---|---|
| 解析器 | lphply (自维护 PyPI 包) |
| 包名 | `phply` |
| 底层实现 | Python Lex-Yacc (PLY) 手写词法/语法分析器 |
| AST 类型 | `phpast` (导入为 `php`) |
| 支持版本 | PHP 5.6 - 8.5 |
| 预解析 | `pretreatment.py` 中并发预解析，结果缓存到 `ast_object` |

## 3. 全局状态变量

```python
# 扫描结果
scan_results = []              # 最终结果列表
scan_chain = ['start']         # 追踪链（用于结果可视化）

# 规则上下文
is_repair_functions = []       # 当前规则的修复函数列表
is_controlled_params = []      # 当前规则的可控参数列表

# 防循环递归
scan_function_stack = []       # 函数调用栈

# 函数摘要缓存
_summaries_initialized = False  # 摘要是否已初始化
_file_summaries = {}            # 文件级函数摘要

# 运行时追踪缓存
_trace_cache = TraceCache("php")  # 变量追踪结果缓存
```

## 4. 入口函数: scan_parser()

```python
def scan_parser(sensitive_func, vul_lineno, file_path,
                repair_functions=[], controlled_params=[], svid=0)
```

### 执行流程

```
scan_parser()
    │
    ├─ 1. _init_function_summaries(file_path)
    │     初始化函数摘要缓存（跨文件分析基础）
    │
    ├─ 2. 重置全局状态
    │     scan_chain = ['start']
    │     scan_results = []
    │     _trace_cache.clear()
    │
    ├─ 3. ast_object.get_nodes(file_path)
    │     从预处理缓存中获取当前文件的 AST 节点列表
    │
    └─ 4. 对每个敏感函数:
         ├─ back_node = []
         ├─ analysis(all_nodes, func, back_node, vul_lineno, file_path)
         └─ scan_results 非空则提前退出
```

## 5. 第一层：AST 节点遍历 — analysis()

```python
def analysis(nodes, vul_function, back_node, vul_lineno, file_path=None, function_params=None)
```

`analysis()` 是 PHP 引擎的**正向遍历引擎**，它从文件的第一条语句开始遍历 AST 节点列表，直到找到 sink 行号对应的节点。

### 5.1 遍历策略

- **提前终止**：`if vul_lineno < node.lineno: break` — 超过目标行号即停止
- **back_node 累积**：每处理一个节点，将其追加到 `back_node` 列表（供后续 `parameters_back` 使用）
- **语法结构穿透**：遇到 `if/while/for/foreach/switch/try/function/class` 等复合结构时，递归进入子节点列表

### 5.2 节点类型分派

| AST 节点类型 | 处理函数 | 说明 |
|---|---|---|
| `FunctionCall` / `MethodCall` / `StaticMethodCall` | `anlysis_function()` | 函数调用（含方法） |
| `Assignment` | `anlysis_function()` / `analysis_eval()` | 赋值表达式的右值 |
| `Return` | `analysis_return()` | return 语句 |
| `Print` / `Echo` | `analysis_echo_print()` | 输出语句 |
| `Silence` (`@`) | 解包后重入 analysis | 错误抑制符 |
| `AssignOp` (`.=` `+=`) | `anlysis_function()` / `analysis_eval()` | 复合赋值 |
| `BinaryOp` | `anlysis_function()` / `analysis_eval()` | 二元运算表达式 |
| `Eval` | `analysis_eval()` | eval 语言结构 |
| `Include` / `Require` | `analysis_file_inclusion()` | 文件包含 |
| `If` | `analysis_if_else()` | 条件分支 |
| `While/DoWhile/For/Foreach` | 递归 analysis | 循环结构 |
| `Switch` | 遍历 cases | switch 结构 |
| `Try` | `analysis_try()` | 异常处理 |
| `Function` / `Method` | 递归 analysis（重建 function_body） | 函数/方法定义 |
| `Class` / `Trait` | 递归 analysis | 类定义 |

### 5.3 关键设计：函数参数捕获

当遍历到 `Function` / `Method` 节点时：

```python
elif isinstance(node, php.Function) or isinstance(node, php.Method):
    function_body = []              # 新建空的函数体节点列表
    function_params = get_function_params(node.params)  # 提取形参名列表
    analysis(node.nodes, vul_function, function_body, vul_lineno,
             function_params=function_params, file_path=file_path)
```

**关键点**：`function_body` 是空列表，在递归 analysis 中会被填充为函数体中的语句。这些语句形成 `back_node`，供 `parameters_back` 回溯使用。

## 6. 第二层：Sink 参数提取 — anlysis_function()

```python
def anlysis_function(node, back_node, vul_function, function_params, vul_lineno, file_path=None)
```

当 `analysis()` 定位到 sink 行号的函数调用节点后，`anlysis_function()` 负责提取 sink 函数的参数，并根据参数类型分派到对应的 `analysis_*_node()` 函数。

### 6.1 定位逻辑

```python
if int(node.lineno) == int(vul_lineno):
    if function_name == vul_function:  # 精确匹配 sink 函数名
        function_params = get_all_functioncall_params(node)  # 提取所有参数
        for param in function_params:
            # 按参数 AST 类型分派
```

### 6.2 参数类型分派

| 参数 AST 类型 | 处理函数 | 回溯策略 |
|---|---|---|
| `Variable` (`$cmd`) | `analysis_variable_node()` | → `anlysis_params()` → `deep_parameters_back()` |
| `FunctionCall` (`trim($x)`) | `analysis_functioncall_node()` | 检查可控性 + 修复函数 → `anlysis_params()` |
| `BinaryOp` (`$a . $b`) | `analysis_binaryop_node()` | 提取所有变量 → 逐个回溯 |
| `ArrayOffset` (`$arr['k']`) | `analysis_arrayoffset_node()` | 直接 `is_controllable()` |
| `Assignment` (`$x = func()`) | 检查左右两侧 | 分别处理 node 和 expr |
| `AssignOp` (`.=` `+=`) | 检查左右两侧 | 分别处理 left 和 right |
| `TernaryOp` (`$a ? $b : $c`) | `analysis_ternaryop_node()` | 分别回溯 true/false 分支 |
| 特殊调用类型 | `analysis_special_functioncall_node()` | 提取参数后回溯 |

### 6.3 关键设计：可控函数调用快速判定

`analysis_functioncall_node()` 中有一个重要的短路逻辑：

```python
# 如果 sink 的参数本身是可控函数调用（例如 system(input('get.id'))）
is_co, cp = is_controllable(function_name)
if is_co == 1:
    set_scan_results(1, cp, expr_lineno, vul_function, node, vul_lineno)
    return True
```

这避免了继续回溯 `input()` 的字面量参数导致漏报。

## 7. 第三层：核心回溯 — parameters_back()

```python
def parameters_back(param, nodes, function_params=None, lineno=0,
                    function_flag=0, vul_function=None, file_path=None,
                    isback=None, parent_node=None)
```

`parameters_back()` 是 PHP 引擎的**核心回溯引擎**，负责从 sink 参数出发，反向追踪变量来源，直到到达可控输入源或确定不可控。

### 7.1 缓存层

```python
def parameters_back(param, nodes, ...):
    # 查缓存
    cached = _trace_cache.get(file_path, str(_pname), int(lineno))
    if cached is not None:
        return cached
    
    # 调用实际实现
    result = _parameters_back_impl(param, nodes, ...)
    
    # 写缓存（仅确定性结果）
    if is_co in (-1, 1, 2):
        _trace_cache.put(file_path, str(_pname), int(lineno), result)
```

### 7.2 _parameters_back_impl 核心逻辑

```
_parameters_back_impl(param, nodes, lineno, ...)
    │
    ├─ Step 1: 初始可控性检查
    │   is_co, cp = is_controllable(param)
    │   如果 param 本身就是 $_GET/$ _POST 等 → 直接返回 (1, cp, 0)
    │
    ├─ Step 2: 按污点类型分派
    │   ├─ FunctionCall → function_back()   进入函数体分析返回值
    │   ├─ ArrayOffset  → array_back()      进入数组赋值追踪
    │   ├─ Include/Require → 替换为 expr 继续追踪
    │   └─ New Class     → new_class_back()  进入 __toString
    │
    ├─ Step 3: 反向遍历 nodes（从最后一个节点向前）
    │   for node in nodes[::-1]:
    │     │
    │     ├─ 行号检查：node.lineno >= lineno → 跳过
    │     │
    │     ├─ Assignment: 找到 param_name = param_expr
    │     │   ├─ 检查是否经过修复函数 → (2, cp, lineno)
    │     │   ├─ is_controllable(param_expr) → 直接判定
    │     │   └─ 不可控 → param = param_expr（污点替换）继续
    │     │
    │     ├─ TernaryOp ($a = $cond ? $x : $y)
    │     │   ├─ 分支约束检查
    │     │   ├─ 等值约束阻断 → (-1, param, 0)
    │     │   └─ 分别追踪 iftrue 和 iffalse
    │     │
    │     ├─ If/ElseIf/Else
    │     │   ├─ _find_sink_branch() 判断 sink 在哪个分支
    │     │   ├─ 提取分支条件约束 (extract_constraints_from_php_expr)
    │     │   ├─ 等值约束阻断检查
    │     │   └─ 递归进入目标分支体
    │     │
    │     ├─ While/DoWhile
    │     │   ├─ while 条件等值约束检查
    │     │   └─ 递归进入循环体
    │     │
    │     ├─ Switch
    │     │   ├─ sink 在非 default case → 阻断 (-1)
    │     │   └─ sink 在 default → 跳过 switch
    │     │
    │     ├─ Try/Catch/Finally
    │     │   ├─ 优先分析 finally（一定执行）
    │     │   └─ try/catch 视为独立分支
    │     │
    │     ├─ For/Foreach
    │     │   ├─ foreach valvar 匹配 → 追踪数组表达式
    │     │   └─ 递归进入循环体
    │     │
    │     ├─ AssignOp (.= +=)
    │     │   └─ 处理复合赋值，提取右值继续追踪
    │     │
    │     ├─ Global
    │     │   └─ param 在 global 列表中 → (5, param, lineno)
    │     │
    │     └─ 其他节点 → 跳过（继续下一个）
    │
    ├─ Step 4: 递归继续
    │   is_co == 3 → parameters_back(param, nodes[:-1], ...)
    │
    └─ Step 5: 函数参数兜底
        nodes 为空且 function_params 非空
        param 在 function_params 中 → (2, param, lineno)
```

### 7.3 污点替换机制（核心设计）

```python
# 在 Assignment 节点中：
if param_name == param_node:  # 找到当前追踪变量的赋值
    param_expr = get_expr_name(node.expr)  # 获取赋值右值
    param = build_ast_param(param_expr)    # 用右值替换当前污点
    param_name = get_node_name(param)      # 更新污点名
# 继续下一次循环，用新污点在 nodes 中继续回溯
```

这就是"污点传播"的核心：每次找到 `$x = expr`，就把追踪目标从 `$x` 切换为 `expr`，逐层向上追溯。

### 7.4 is_controllable() — 可控性判定

```python
def is_controllable(expr, flag=None):
    # 内置可控参数
    controlled_params = ['$_GET', '$_POST', '$_REQUEST', '$_COOKIE', '$_FILES', ...]
    controlled_params += is_controlled_params  # 合并规则传入的

    # ArrayOffset: $_GET['id'] → (1, '$_GET')
    # ObjectProperty → (3, expr)  # 未确认
    # FunctionCall:
    #   修复函数 → (2, expr)
    #   可控函数 → (1, expr)
    #   其他 → (3, expr)
    # Variable:
    #   在 controlled_params 中 → (1, Variable)
    #   以 $ 开头 → (3, Variable)
    #   其他 → (-1, Variable)
```

返回值语义：
- **1**：可控（确认是外部输入）
- **2**：可控但已修复
- **3**：未确认（变量，需继续回溯）
- **-1**：不可控（字面量、常量等）

## 8. 函数调用回溯 — function_back()

```python
def function_back(param, nodes, function_params, vul_function=None, file_path=None, isback=None)
```

当回溯到函数调用节点时（如 `$x = get_data()`），需要进入函数体分析返回值是否可控。

### 8.1 防循环递归

```python
if function_name in scan_function_stack:
    return -1, cp, expr_lineno  # 检测到循环调用，直接返回不可控
scan_function_stack.append(function_name)
# ... 分析逻辑 ...
scan_function_stack.pop()
```

### 8.2 三级分析策略

```
function_back(func_call_node, nodes, ...)
    │
    ├─ Level 1: 内置知识库查询
    │   _trace_cache.lookup_builtin(function_name)
    │   ├─ safe=True, passthrough=[] → (-1, ...)  安全函数，不可控
    │   ├─ passthrough=[0] → ('deps', [实参变量名], ...)
    │   └─ 其他 → (-1, ...)
    │
    ├─ Level 2: 函数摘要查询
    │   lookup_summary(function_name) → _judge_from_summary_php()
    │   ├─ return_flow 中 origin_type='param' 且实参可控 → (1, ...)
    │   ├─ return_flow 中 origin_type='global' 可控 → (1, ...)
    │   └─ 未确认 → 继续下一级
    │
    └─ Level 3: 完整 AST 分析
        在 nodes 中查找函数定义 → _analyze_return_deps()
        ├─ 建立形参→实参映射
        ├─ 函数体内赋值链传播（最多 3 轮迭代）
        ├─ 查找 return 语句分析依赖
        └─ 形参→实参映射得到调用者变量 → ('deps', [...], ...)
```

### 8.3 deps 机制（核心创新）

`function_back()` 不直接返回 `is_co=1`，而是返回 `('deps', [变量名列表], expr_lineno)`。由调用方的 `parameters_back()` 继续向上追踪这些依赖变量：

```python
if isinstance(is_co, str) and is_co == 'deps' and isinstance(cp, list):
    for dep_var in cp:
        is_co2, cp2, expr_lineno2 = parameters_back(
            build_ast_param(dep_name), nodes[:-1], ...)
        if is_co2 == 1:
            return is_co2, cp2, expr_lineno2
    return 3, param, expr_lineno  # 所有依赖变量都没找到可控来源
```

这避免了在函数体内调用 `parameters_back` 导致的循环递归问题。

### 8.4 _analyze_return_deps() 详解

这是函数体分析的完整实现：

```
_analyze_return_deps(called_func, function_body, call_node)
    │
    ├─ 1. 建立形参→实参映射
    │     formal_params = ['$a', '$b']
    │     actual_params = [Variable('$x'), Constant(1)]
    │     arg_map = {'$a': Variable('$x'), '$b': Constant(1)}
    │
    ├─ 2. 收集可控形参
    │     '$x' 可控 → controllable_formal = {'$a'}
    │
    ├─ 3. 赋值链传播（3 轮迭代）
    │     $c = $a → $c 也标记为可控
    │
    └─ 4. 分析 return 语句
         ├─ return $_GET['id'] → is_controllable() = 1 → 直接返回
         ├─ return trim($input) → is_repair() → (2, ...)
         ├─ return $c → $c 在 controllable_local 中
         │   → 取 arg_map['$a'] = Variable('$x')
         │   → is_controllable('$x') = 1 → (1, ...)
         ├─ return $c → $c 依赖 '$a' → ('deps', ['$x'], ...)
         └─ 无明确来源但有实参变量 → ('deps', caller_var_names, ...)
```

## 9. 深度回溯 — deep_parameters_back()

```python
def deep_parameters_back(param, back_node, function_params, count, file_path, lineno, vul_function, isback)
```

当 `parameters_back()` 返回 `is_co=3`（未确认）时，`deep_parameters_back()` 尝试更深入的追踪：

### 9.1 include 文件跨文件追踪

```python
if is_co == 3:
    for node in back_node[::-1]:
        if isinstance(node, php.Include):
            # 解析 include 路径
            filename = get_filename(node, file_path)
            # 构造新 file_path
            # 获取新文件的 AST 节点
            all_nodes = ast_object.get_nodes(new_file_path)
            # 在新文件中继续回溯
            is_co, cp, expr_lineno = deep_parameters_back(
                param, new_vul_nodes, function_params, count+1, new_file_path, ...)
```

### 9.2 深度限制

```python
if count > 20:
    logger.warning("[Deep AST] depth too big, auto exit...")
    return is_co, cp, expr_lineno
```

## 10. 分支约束追踪

### 10.1 _find_sink_branch()

判断 sink 行号位于 if/else 的哪个分支：

```python
def _find_sink_branch(if_node, lineno):
    # 返回: 'if', 'elseif_N', 'else', 'outside'
    # 基于 phply AST 行号规则：
    #   If.lineno = if 关键字行号
    #   ElseIf.lineno = elseif 关键字行号
    #   Else.lineno = else 关键字行号
```

### 10.2 extract_constraints_from_php_expr()

从 PHP 条件表达式提取 `BranchConstraint`：

```
isset($var)           → BranchConstraint('$var', 'isset')
!isset($var)          → BranchConstraint('$var', '!isset')
$var === 'admin'      → BranchConstraint('$var', '===', 'admin')
$a == "x" || $a == "y" → BranchConstraint('$a', 'in', ['x', 'y'])
$a && $b              → [约束_a, 约束_b]（两个都要满足）
```

### 10.3 约束阻断逻辑

```python
# if 分支：直接使用条件约束
if sink_branch == 'if':
    constraints = extract_constraints_from_php_expr(node.expr)

# else 分支：取反条件
if sink_branch == 'else':
    constraints = [c.negate() for c in extract_constraints_from_php_expr(node.expr)]

# 检查等值约束是否阻断
for c in constraints:
    if c.var_name == param_name and c.op in ('==', '===', 'in'):
        return -1, param, 0  # 变量被限定为固定值，不可控
```

### 10.4 三元表达式约束

```python
# $result = ($type == 'admin') ? $safe_value : $user_input;
# 如果 $type == 'admin' 约束且追踪变量只在 false 分支 → 不阻断，追踪 false 分支
# 如果约束变量只在 true 分支 → 阻断（true 路径中值固定）
```

## 11. 完整数据流示例

以 `system($_GET['cmd'])` 为例：

```
scan_parser(['system'], 10, '/app/index.php')
    │
    ├─ analysis(all_nodes, 'system', back_node=[], vul_lineno=10)
    │   遍历到 FunctionCall(name='system', lineno=10)
    │   ├─ anlysis_function(node, back_node, 'system', None, 10)
    │   │   ├─ lineno==10, name=='system' ✓
    │   │   ├─ params = [Parameter(ArrayOffset(Variable('$_GET'), 'cmd'))]
    │   │   └─ analysis_arrayoffset_node(param, 'system', 10)
    │   │       ├─ param = '$_GET'
    │   │       ├─ is_controllable('$_GET') → (1, Variable('$_GET'))
    │   │       └─ set_scan_results(1, Variable('$_GET'), 10, 'system', param, 10)
    │   └─ scan_results = [{'code': 1, 'source': Variable('$_GET'), ...}]
    │
    └─ return [{'code': 1, ...}]
```

以 `$cmd = get_input(); system($cmd);` 为例：

```
scan_parser(['system'], 12, '/app/index.php')
    │
    ├─ analysis(all_nodes, 'system', back_node=[], vul_lineno=12)
    │   │
    │   ├─ Line 10: Function('get_input') → analysis 递归进入，填充 function_body
    │   │   back_node = [..., Function('get_input', nodes=[...])]
    │   │
    │   ├─ Line 11: Assignment($cmd = FunctionCall('get_input'))
    │   │   back_node = [..., Function('get_input'), Assignment($cmd = get_input())]
    │   │
    │   └─ Line 12: FunctionCall('system', lineno=12) == vul_lineno
    │       └─ anlysis_function(node, back_node, 'system', None, 12)
    │           ├─ params = [Variable('$cmd')]
    │           └─ analysis_variable_node(Variable('$cmd'), back_node, 'system', 12)
    │               └─ anlysis_params('$cmd', file_path, 12)
    │                   ├─ all_nodes = ast_object.get_nodes(file_path)
    │                   ├─ vul_nodes = [nodes where lineno <= 12]
    │                   └─ deep_parameters_back(Variable('$cmd'), vul_nodes, None, 0, file_path, 12)
    │                       └─ parameters_back(Variable('$cmd'), vul_nodes, lineno=12, ...)
    │                           │
    │                           ├─ is_controllable('$cmd') → (3, Variable('$cmd'))
    │                           │
    │                           ├─ 遍历 nodes (反向):
    │                           │   ...
    │                           │   Assignment($cmd = FunctionCall('get_input'))
    │                           │   ├─ param_name='$cmd' == node.node.name='$cmd' ✓
    │                           │   ├─ param_expr = FunctionCall('get_input')
    │                           │   ├─ is_controllable(FunctionCall('get_input')) → (3, ...)
    │                           │   ├─ param = FunctionCall('get_input')（污点替换）
    │                           │   │
    │                           │   ├─ FunctionCall → function_back()
    │                           │   │   ├─ scan_function_stack = ['get_input']
    │                           │   │   ├─ 内置知识库 → 未找到
    │                           │   │   ├─ 函数摘要 → 未找到
    │                           │   │   ├─ 找到 Function('get_input') 定义
    │                           │   │   └─ _analyze_return_deps()
    │                           │   │       ├─ 形参: 无
    │                           │   │       ├─ return $_POST['data']
    │                           │   │       ├─ is_controllable('$_POST['data']') → (1, ...)
    │                           │   │       └─ return (1, Variable('$_POST'), lineno)
    │                           │   │
    │                           │   └─ function_back returns (1, Variable('$_POST'), lineno)
    │                           │
    │                           └─ return (1, Variable('$_POST'), 8)
    │
    └─ scan_results = [{'code': 1, 'source': Variable('$_POST'), 'source_lineno': 8, ...}]
```

## 12. 特殊处理

### 12.1 文件包含跨文件追踪

PHP 的 `include/require` 可以引入外部文件。`deep_parameters_back()` 会：
1. 在 `back_node` 中搜索 `Include` 节点
2. 解析 include 路径（处理变量拼接）
3. 加载目标文件的 AST
4. 在目标文件中继续回溯变量

### 12.2 类分析

- `class_back()` — 进入类体追踪变量，包括构造函数 `__construct` 的参数
- `new_class_back()` — 对新建类进入 `__toString()` 方法分析
- 当函数参数来自类构造函数时返回 `code=4`（新规则生成信号）

### 12.3 全局变量

```python
# 遇到 global 语句时：
if isinstance(node, php.Global):
    if param_name in global_params:
        return 5, param, node.lineno  # 特殊返回码，表示需要在外层作用域追踪
```

### 12.4 eval 语言结构

`eval()` 在 PHP 中是语言关键字而非函数，需要特殊处理：
- `analysis_eval()` 在 sink 行号匹配 `eval` 时触发
- 回溯 `eval` 的参数表达式

### 12.5 Silence 操作符 (`@`)

```python
# @func() → 解包为 func() 的参数后重入 analysis
nodes = get_silence_params(node)
analysis(nodes, vul_function, back_node, ...)
```

## 13. 函数摘要系统

### 13.1 初始化

```python
def _init_function_summaries(file_path):
    cache_mgr = SummaryCacheManager()
    cached = cache_mgr.load_or_generate(target_dir, files_dict)
    _file_summaries = cached
```

### 13.2 查询

```python
def lookup_summary(function_name):
    if not _file_summaries:
        return None
    for fp, fs in _file_summaries.items():
        for fn in fs.functions:
            if fn.name == function_name:
                return fn
    return None
```

### 13.3 摘要判定

```python
def _judge_from_summary_php(summary, call_node):
    # 遍历 return_flow:
    #   origin_type='param' → 检查实参可控性
    #   origin_type='global' → 检查全局变量可控性
    #   origin_type='call' → 检查函数调用可控性
    #   origin_type='literal' → 跳过
```

## 14. PHP 引擎文件结构

```
core/core_engine/php/
├── parser.py              # 主引擎 (3241行)
├── summary_generator.py   # 函数摘要生成器
└── builtin_knowledge.py   # 内置函数可控性知识库
```

## 15. 与其他引擎的差异

| 特性 | PHP | JS | Python | Java | Go | C |
|---|---|---|---|---|---|---|
| 解析器 | lphply | esprima | ast | javalang | go/ast | tree-sitter |
| 行数 | 3241 | 2543 | 2050 | ~1962 | ~1800 | ~2323 |
| 回溯方向 | 正向遍历+反向回溯 | 反向回溯 | 表达式级回溯 | 反向回溯 | Go AST 回溯 | 文本+AST 混合 |
| 函数回溯 | function_back + deps | function_back | _trace_function_return | function_back_java | function_back_go | function_back_c |
| 对象传播 | class_back | member_back | _trace_cross_file_self | _propagate_object_taint | - | - |
| 跨文件 | deep_parameters_back (include) | 自动搜索 | _trace_cross_file | 自动搜索 | 自动搜索 | 头文件分析 |
