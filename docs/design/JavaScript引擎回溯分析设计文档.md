# JavaScript 引擎回溯分析设计文档

> 源文件：`core/core_engine/javascript/parser.py`（2543 行）
> 辅助模块：`builtin_knowledge.py`、`summary_generator.py`、`engine.py`
> 解析器：esprima（Python binding，通过 `from esprima import nodes as jsnodes`）

---

## 1. 引擎概述

JavaScript 引擎是 Kunlun-M 中覆盖场景最复杂的引擎之一，需要处理浏览器端 DOM 操作、Chrome 扩展 API、Node.js 服务端框架（Express/Koa/Hapi/Fastify）三大场景。与 PHP 引擎相比，JS 引擎独有的挑战包括：

- **原型链（prototype）追踪**：`new Foo()` + `Foo.prototype.method = xxx` 的对象方法重载
- **闭包（IIFE）追踪**：`(function(a){return a})(x)` 立即执行函数的参数映射
- **ES6 Class 追踪**：`this.xxx` 跨方法属性传播
- **async/await**：`await expr` 中的嵌套调用分析
- **对象字面量中的方法传递**：`{ method: vulnerableFunc }` 的 eval method 检测

引擎总行数 2543 行，是仅次于 PHP（3241 行）的第二大引擎。

---

## 2. 全局状态变量

JS 引擎通过模块级全局变量在函数间传递分析状态（与 PHP 引擎一致的设计模式）：

```python
scan_results = []           # 扫描结果列表
is_repair_functions = []   # 修复函数列表
is_controlled_params = []  # 可控参数列表（规则传入 + 用户自定义）
scan_chain = []            # 回溯链路追踪记录

_trace_cache = TraceCache("javascript")  # 追踪缓存（单例）
_summaries_initialized = False            # 函数摘要是否已初始化
_file_summaries = {}                     # 文件级函数摘要缓存

_this_prop_map = {}                      # Class 属性映射：{prop_name: AST_node}
_class_method_param_map = {}             # Class 方法参数映射：{method_name: {param_idx: prop_name}}
```

### 2.1 默认可控参数（default_controlled_params）

JS 引擎内置了一份远比 PHP 更丰富的可控源列表，覆盖三大运行环境：

**浏览器端（DOM/BOM）**：
```python
'location.hash', 'document.cookie', 'location.search',
'location.href', 'window.name', '.addEventListener'
```

**Chrome 扩展 API**：
```python
'chrome.tabs.query', 'chrome.tabs.get', 'chrome.cookies.get',
'chrome.runtime.onMessage.addListener', ...
```

**Node.js 服务端框架**：

| 框架 | 可控源 |
|------|--------|
| Express | `req.query`, `req.body`, `req.params`, `req.headers`, `req.cookies`, `req.files` |
| Koa | `ctx.query`, `ctx.params`, `ctx.request.body`, `ctx.request.query`, `ctx.request.header` |
| Hapi | `request.query`, `request.params`, `request.payload`, `request.headers` |
| Fastify | `request.query`, `request.body`, `request.params`, `request.headers` |

**Node.js 原生**：`process.env`, `process.argv`, `req.url`, `req.method`, `req.headers`

注意 `req.query.` 和 `req.body.` 这种带点号后缀的写法，用于支持 `req.query.id` 这样的嵌套属性匹配（substring 匹配）。

---

## 3. AST 辅助函数层

JS 引擎有一组底层 AST 节点访问函数，所有上层回溯逻辑都依赖它们：

### 3.1 get_member_data (line 121)

从 AST 节点提取"可读名称"字符串，是整个引擎使用频率最高的函数：

```python
def get_member_data(node, check=False, isparam=False, isclean_prototype=False, isreverse=False)
```

| 节点类型 | 返回值 | 说明 |
|----------|--------|------|
| Identifier | `node.name` | 如 `'data'` |
| Literal | `node.value` | 如 `'hello'`，check=True 时返回 `'1'`（常量标记） |
| MemberExpression | `'obj.prop'` | 递归拼接 object.property |
| AssignmentExpression | `'left=right'` | 拼接左右两侧 |
| CallExpression | `'funcName(arg1,arg2)'` | 拼接函数名和参数列表 |
| 其他 | `str(node)` | 兜底 |

关键 flags：
- `isparam=True`：MemberExpression 只返回 object 名（用于 `new Foo()` 中的类名提取）
- `isclean_prototype=True`：过滤掉 `prototype` 属性
- `isreverse=True`：Literal 值反转（用于 `Array.reverse()` 的特殊处理）

### 3.2 get_original_object / get_property_object (line 271/280)

```python
def get_original_object(node)   # 获取 MemberExpression 的 object 部分
def get_property_object(node)   # 获取 MemberExpression 的 property 部分
```

例如 `obj.method` → `get_original_object` 返回 `obj` 节点，`get_property_object` 返回 `'method'`。

### 3.3 get_param_list / get_param (line 262/220)

```python
def get_param_list(param_nodes, is_eval=False, is_function_regex=True)
def get_param(call_expression, is_eval=False)
```

`get_param_list` 从 AST 参数节点列表中提取可追踪的参数。`get_param` 专门处理 CallExpression 的参数提取，支持 `is_eval` 模式下对 `eval`/`setTimeout` 的特殊处理。

### 3.4 is_memberexp / generate_memberexp / set_original_object (line 331/312/288)

- `is_memberexp(node)`：判断节点是否为 MemberExpression
- `generate_memberexp(obj, prop, lineno)`：构造一个新的 MemberExpression AST 节点
- `set_original_object(node, new_obj)`：修改 MemberExpression 的 object 部分（对象合并操作）

### 3.5 check_param (line 402)

将字符串形式的参数名转换为对应的 esprima AST 节点，用于外部入口（isexternal）模式下的参数重建。

---

## 4. 可控性判定：is_controllable

```python
def is_controllable(param):  # line 369
```

### 4.1 返回码体系

| 返回码 | 含义 |
|--------|------|
| -1 | 不可控（字面量、常量） |
| 1 | 用户可控 |
| 2 | 已修复（safe 函数） |
| 3 | 未知（普通变量、函数调用、对象属性，需继续追踪） |
| 4 | 新函数规则生成 |

### 4.2 判定逻辑

```python
is_co = 3
real_param = get_member_data(param, True)
controlled_params = is_controlled_params + default_controlled_params

if real_param == 1:
    is_co = -1  # 字面量常量

for controlled_param in controlled_params:
    if controlled_param in str(real_param):
        is_co = 1  # substring 匹配
```

**核心设计**：使用 **substring 匹配**（`in` 运算符）而非精确匹配。这允许 `req.query` 匹配 `req.query.id`，`req.body.` 匹配 `req.body.data`。这是一个有意的精度牺牲——通过降低精确度来提高覆盖率。

与 PHP 引擎的差异：PHP 使用精确的 `==` 比较且硬编码了 `$_GET`/`$_POST` 等超全局变量列表；JS 引擎使用 `in` substring 匹配，更灵活但也可能带来更多误报。

---

## 5. 前向扫描：从文件入口到 Sink 定位

### 5.1 scan_parser 入口 (line 2504)

```python
def scan_parser(sensitive_func, vul_lineno, file_path,
                repair_functions=[], controlled_params=[]):
```

执行流程：
1. **清空全局状态**：`_trace_cache.clear()`，重置 `_summaries_initialized`
2. **初始化函数摘要**：`_init_function_summaries(file_path)` 加载/生成当前项目的函数摘要缓存
3. **初始化扫描链**：`scan_chain = ['start']`
4. **获取 AST**：通过 `ast_object.get_nodes(file_path)` 获取 esprima 解析后的 AST 根节点
5. **遍历敏感函数**：对每个 `func in sensitive_func`，调用 `analysis(all_nodes, func, ...)`
6. **首次即退出**：一旦 `scan_results` 非空立即 break

### 5.2 analysis 主分发器 (line 2264)

```python
def analysis(all_nodes, vul_function, back_node, vul_lineno, file_path,
            function_params, in_funtion=False):
```

这是前向扫描的核心调度函数，按行号递增顺序遍历 AST 节点：

```
for node in all_nodes:
    if vul_lineno < node.loc.start.line:
        break  # 超过 sink 行号，停止扫描

    if not in_funtion:
        back_node.append(node)  # 追加到回溯上下文

    根据 node.type 分发处理：
    ├── ExpressionStatement → analysis_expression()
    ├── FunctionDeclaration → 递归进入函数体
    ├── BlockStatement → 递归进入块
    ├── IfStatement → analysis_If()
    ├── SwitchStatement → 遍历 case 分支
    ├── VariableDeclaration → 追加到 back_node + 检查 init 类型
    ├── TryStatement → 进入 try 块
    ├── ClassDeclaration → ES6 Class 处理（两阶段）
    └── WhileStatement → analysis_while()
```

**back_node 设计**：这是一个在 analysis 遍历过程中动态构建的列表，记录了从文件开头到 sink 之间经过的所有"有意义的"节点。`parameters_back` 回溯时使用 `nodes[len(nodes)-1]` 取最后一个节点（即最近的一条语句），逐步向前推进。**非函数体内的节点**通过 `in_funtion=False` 控制，只追加顶层节点；**函数体内**的 VariableDeclaration 也会追加（确保局部变量可被回溯到）。

### 5.3 analysis_callexpression (line 2062)

处理 `CallExpression` 节点，分两种情况：

**情况 A：sink 行 == call 行**（`vul_lineno == node.loc.start.line`）
1. 递归处理嵌套的 CallExpression 参数
2. 若是 `eval`/`setTimeout` → `analysis_params(is_eval=True)`
3. 若 callee 是 `FunctionExpression`/`ArrowFunctionExpression` → 递归进入函数体
4. 否则 → 检查 `_class_method_param_map` 更新 `_this_prop_map` → `analysis_params()`

**情况 B：sink 在 call 内部**（`vul_lineno > call.start.line`）
1. 若 callee 是函数表达式 → 递归进入
2. 否则 → 遍历参数中的回调函数（如 `fs.readFile(path, function(data){...})`），构造 `callback_back_node` 递归进入回调体

**Class 方法调用追踪**（line 2084-2095）：
```python
if callee_method in _class_method_param_map:
    for arg_idx, prop_name in _class_method_param_map[callee_method].items():
        if arg_idx < len(call_arguments):
            _this_prop_map[prop_name] = call_arguments[arg_idx]
```
当检测到 `obj.setCommand(req.query.cmd)` 这样的调用时，将实参 `req.query.cmd` 存入 `_this_prop_map['cmd']`，后续 `this.cmd` 回溯时可以直接映射。

### 5.4 ES6 Class 处理 (line 2343-2388)

ClassDeclaration 采用**两阶段分析**：

**第一阶段：构建属性映射**
```
遍历 class body 中所有 ClassMethod：
  扫描方法体中的 this.xxx = yyy 赋值
  构建 _this_prop_map[prop_name] = right_value
  如果右值是方法参数 → 构建 _class_method_param_map[method_name] = {param_idx: prop_name}
```

**第 1.5 阶段：解析方法调用实参**
```
如果 _class_method_param_map 非空：
  调用 _resolve_class_method_calls(all_nodes, ...) 在全文件 AST 中搜索方法调用
  将实参写入 _this_prop_map
```

**第二阶段：进入 sink 所在方法体**
```
找到包含 vul_lineno 的 ClassMethod
构造 callback_back_node = list(back_node) + child_nodes
递归 analysis(child_nodes, ..., in_funtion=True)
```

这个两阶段设计的核心动机是：`this.xxx` 的赋值可能发生在构造函数中（`constructor(data) { this.cmd = data; }`），而 sink 可能发生在另一个方法中（`render() { eval(this.cmd); }`）。需要先全局收集 this 属性映射，再在 sink 所在方法体中分析。

### 5.5 analysis_params — Sink 参数提取 (line 1960)

```python
def analysis_params(expression, back_node, vul_function, vul_lineno, file_path,
                    repair_functions=None, controlled_params=None,
                    isexternal=False, is_eval=False, is_function=False):
```

这是从前向扫描切换到**后向回溯**的转折点。核心逻辑：

1. 根据 expression 类型提取参数列表 `param_list`：
   - 普通函数：`get_param_list(expression.arguments)`
   - eval/setTimeout：`get_param_list(expression.arguments, is_eval=True)`
   - 外部模式：`check_param()` 重建 AST 节点
2. 记录 `scan_chain.append(('NewFind', ...))`
3. 对每个参数调用 `deep_parameters_back()` 开始回溯
4. 调用 `set_scan_results()` 收集结果

---

## 6. 后向回溯：从 Sink 参数到 Source 判定

### 6.1 deep_parameters_back (line 1928)

```python
def deep_parameters_back(param, back_node, function_params, count, file_path,
                         lineno=0, vul_function=None, isback=False):
```

简单的递归深度控制包装器：
1. `count += 1`
2. 调用 `parameters_back()` 执行实际回溯
3. 缓存确定性结果（仅 -1/1/2）
4. 深度限制：`count > 20` 时自动退出（防止无限递归）

### 6.2 parameters_back — 核心回溯引擎 (line 1176)

这是 JS 引擎最核心、最复杂的函数，承担所有参数回溯逻辑。

```python
def parameters_back(param, nodes, function_params=None, lineno=0,
                    function_flag=0, vul_function=None, file_path=None,
                    isback=None, method_name=None):
```

#### 6.2.1 回溯入口逻辑

```
① 查缓存 → 命中则直接返回
② is_controllable(param) 判定
③ this 属性映射（字符串版本）：this.xxx → _this_prop_map[xxx] 递归
④ this 属性映射（AST 节点版本）：同上
⑤ 根据 param.type 分发：
   ├── MemberExpression → member_back()
   ├── NewExpression → new_back()
   ├── CallExpression → function_call_back()
   ├── ExpressionStatement(含 CallExpression) → function_call_back()
   └── 其他 → 继续变量赋值追踪
```

#### 6.2.2 变量赋值追踪（核心路径）

当 `nodes` 是列表且最后一个节点匹配时：

**VariableDeclarator（`var x = expr`）**：
```
if param_name == get_member_data(node.id):
    param_expr = node.init  # 右值

    记录 scan_chain: ('Assignment', 'x=expr', file_path, lineno)
    is_controllable(param_expr)

    if is_co == 1: return  # 直接可控

    三元运算符分支约束（ConditionalExpression）:
    → extract_constraints_from_js_expr()
    → _collect_js_var_names() 分别收集 true/false 分支变量
    → 如果约束变量只在 true 分支且 op == '===' → 阻断（return -1）
    → 如果约束变量只在 false 分支 → 追踪 false 分支的 alternate

    if isback: return  # 只需找到一次来源

    右值类型分发：
    ├── MemberExpression → get_original_object + parameters_back(isback=True) + set_original_object（对象合并）
    ├── CallExpression → 提取 callee 继续回溯
    └── 其他 → get_original_object 后继续
```

**ExpressionStatement（`x = expr`）**：
```
逻辑类似 VariableDeclarator，额外处理：
├── BinaryExpression("+") → get_param 拆分多个子参数分别回溯
├── 左值为 MemberExpression → 追踪右值
└── 对象传递检测 → is_co = 4（新函数规则生成）
```

#### 6.2.3 对象传递与新函数规则（is_co = 4）

JS 引擎独有的"对象传递"检测：

```javascript
var executor = new Executor();
executor.setCommand = eval;    // 检测到 is_co=4，记录新的 eval 函数名
executor.setCommand(data);     // 后续分析会用 executor.setCommand 作为新的 sink
```

当检测到 `expression.left` 的值等于 `vul_function`（恶意函数名），标记 `is_co = 4`，`cp = (new_function_name, "evalobject", vul_function)`，后续扫描会用新函数名匹配。

### 6.3 member_back — 对象属性回溯 (line 612)

```python
def member_back(param, nodes, function_params, file_path=None, isback=False,
                vul_function=None, method_name=None):
```

处理 `obj.method` 形式的参数回溯：

1. 如果 object 是 `this` → 返回 `(3, param)`（交给 `parameters_back` 中的 this 映射处理）
2. **递归回溯 object**：`parameters_back(param_object, ..., isback=True, method_name=param_property)`
3. 如果回溯结果为 ObjectExpression → 在对象字面量的 properties 中查找匹配 method_name 的属性
4. 如果找到且值为 FunctionExpression → `function_back()` 分析返回值
5. 如果找到且值为 `this.xxx` → 在同一对象中查找 `this.xxx` 的赋值值（self-reference 解析）

### 6.4 new_back — 原型链回溯 (line 703)

```python
def new_back(param, nodes, function_params, ...)
```

处理 `new ClassName()` 场景，反向遍历 nodes 查找：

1. **FunctionDeclaration** 匹配类名 → 找到构造函数（当前未深入处理）
2. **ExpressionStatement** 中的赋值操作：
   - `ClassName.prototype = otherClass` → 对象重载，继续回溯 `otherClass`
   - `ClassName.prototype.method = xxx` → 原型方法修改，继续回溯 `xxx`

### 6.5 function_call_back — 函数调用回溯 (line 795)

```python
def function_call_back(param, nodes, function_params, file_path=None, isback=False,
                       vul_function=None, method_name=None):
```

处理右值为 `CallExpression`（如 `x = foo(y)` 中的 `foo(y)`）的回溯：

**优先级分发链**：

```
① callee == vul_function → 恶意函数的递归调用，追踪参数
② callee.type == FunctionExpression → 闭包处理 (IIFE)
③ callee.type == MemberExpression → 方法调用
   ├── 检查 JS_BUILTIN_KNOWLEDGE（如 "reverse" 特殊处理）
   └── 回溯 expression_object
④ callee_name in JS_BUILTIN_KNOWLEDGE → 内置函数，追踪参数
⑤ else → 用户自定义函数
   ├── 查 lookup_builtin（内置知识库补充）
   ├── 查 lookup_summary（函数摘要）
   │   └── _judge_from_summary_js()
   └── 反向遍历 nodes 找 FunctionDeclaration
       └── function_back() 分析
```

**闭包处理**（`function_call_back` 中 `expression.type == "FunctionExpression"`）：
```javascript
(function(a){ return a; })(externalData)
```
1. 在闭包体中找到 ReturnStatement
2. `parameters_back(return_expr, callee_body, ...)` 回溯 return 值
3. 如果未确定 → 检查 return 值是否匹配形参
4. 匹配则将闭包实参映射为外部参数，继续 `parameters_back(closure_arg, nodes[:-1], ...)`

### 6.6 function_back — 函数体分析 (line 488)

```python
def function_back(function_node, function_params, back_nodes=None, file_path=None,
                  isback=False, vul_function=None, method_name=None, iscall=False):
```

**设计哲学**：不再进入函数体内调用 `parameters_back`（避免循环递归），而是分析 return 表达式依赖哪些变量，返回 **deps（依赖列表）** 由外层映射。

**执行流程**：
1. 查内置知识库 → `safe=True` 返回 -1；`passthrough` 返回 `('deps', [形参名])`
2. 在函数体中找最后一个 ReturnStatement
3. 如果返回 `this` → 返回 `(3, param)`（交给外层处理）
4. `is_controllable(return_expr)` → 如果可控返回 1
5. `_collect_js_var_names(return_expr)` 收集 return 表达式中所有变量名
6. 匹配函数形参列表 → 如果有匹配：
   - `iscall=True` → 返回 `(4, matched_param_name)` 由外层映射实参
   - `iscall=False` → 生成新函数规则 `(4, (function_node.id, cp, vul_function))`
7. 没有匹配形参但有变量引用 → 返回 `('deps', [变量名列表])`

**deps 机制是 JS 引擎避免函数体内循环递归的关键设计**。通过在函数边界收集"return 表达式依赖哪些变量名"，然后在调用者上下文中将变量名映射为实参继续追踪，完全跳过了函数体内部的 statements 分析。

---

## 7. 分支约束提取

### 7.1 _find_sink_branch_js (line 1054)

```python
def _find_sink_branch_js(if_node, lineno) → 'if' | 'else' | 'outside'
```

判断 sink 行号位于 if/else 的哪个分支：

```python
# if 体范围
if_nodes = if_body.body  (或 [if_body] 如果非 BlockStatement)
if first.start.line <= lineno <= last.end.line: return 'if'

# else 体范围
if alternate 是 IfStatement → 递归（else if 链）
if alternate 是 BlockStatement → 检查行号范围
```

支持嵌套的 `if-else if-else` 链。

### 7.2 extract_constraints_from_js_expr (line 1085)

从 JS 条件表达式（`toDict()` 后的字典格式）提取 `BranchConstraint` 列表。

**支持的 AST 模式**：

| 条件语法 | AST 类型 | 处理方式 |
|----------|----------|----------|
| `x === "string"` | BinaryExpression(op='===') | 提取 var_name + value |
| `x !== null` | BinaryExpression(op='!==') | 提取 + negate |
| `typeof x === "string"` | BinaryExpression(op='===', left=UnaryExpression) | 递归到 UnaryExpression 内部 |
| `!expr` | UnaryExpression(op='!') | 递归取反 |
| `x && y` | LogicalExpression(op='&&') | 合并两侧约束 |
| `x \|\| y` | LogicalExpression(op='\|\|') | 枚举模式检测：同一变量不同值 → `in` 约束 |

**辅助函数**：
- `_extract_js_var_name(node)` (line 1145)：从 AST 节点提取变量名（Identifier → name，MemberExpression → `obj.prop`）
- `_extract_js_literal(node)` (line 1162)：提取字面量值（Literal → value，`null` → None，`undefined` → `'__undefined__'`）

### 7.3 三元运算符约束（parameters_back 中内联）

在 `parameters_back` 的 VariableDeclarator 分支中，当右值为 `ConditionalExpression` 时：

```javascript
var data = (typeof input === 'string') ? safeValue : userInput;
```

处理逻辑：
1. 分别收集 true/false 分支的变量名（`_collect_js_var_names`）
2. 从 test 表达式提取约束（`extract_constraints_from_js_expr`）
3. 如果约束变量**只在 true 分支出现**且 op 为 `==`/`===`/`in` → **阻断**（约束变量被固定值绑定，污点不可能到达该分支）
4. 如果约束变量**只在 false 分支出现** → 追踪 false 分支的 alternate 表达式

---

## 8. 函数摘要机制

### 8.1 _init_function_summaries (line 2396)

```python
def _init_function_summaries(file_path):
```

1. 从 `ast_object` 获取目标目录
2. 收集所有 JS 文件内容 `files_dict`
3. 通过 `SummaryCacheManager.load_or_generate()` 加载缓存
4. 对缓存未命中的文件调用 `generate_summaries_for_target()` 生成
5. 保存到 `_file_summaries` 全局字典

### 8.2 _judge_from_summary_js (line 2453)

```python
def _judge_from_summary_js(summary, call_args) → (code, source, lineno) | None
```

遍历 `summary.return_flow` 中的每个 `ReturnFlowItem`：

| origin_type | 处理逻辑 |
|-------------|----------|
| `param` | 检查 `dep_params` 对应的实参是否可控；不可控则收集变量名返回 deps |
| `global` | 检查 origin 是否包含可控参数 |
| `call` | 先检查可控参数；查 builtin_knowledge passthrough；最后追踪 dep_params |
| `literal` | 跳过 |

### 8.3 summary_generator.py

独立模块，提供 `generate_file_summaries()` 和 `generate_summaries_for_target()` 函数，以及 `lookup_summary(func_name)` 查询接口。通过遍历函数 AST 生成 `FunctionSummary` 对象，包含 `return_flow: List[ReturnFlowItem]`。

---

## 9. 特殊场景处理

### 9.1 eval / setTimeout 特殊处理

```python
special_eval_function = ["eval", "setTimeout"]
```

`is_eval_function(node)` 判断 callee 是否为 eval/setTimeout。对于这类函数，整个表达式字符串就是危险参数（而非单个参数），因此使用 `is_eval=True` 模式提取参数。

### 9.2 对象字面量方法传递

```javascript
var obj = {
    render: document.write   // eval method 传递
};
```

`analysis_objectexpression()` (line 2128) 检测对象字面量中属性值是否等于 `vul_function`，生成新的 sink 名 `{objectName}.{methodKey}`。

### 9.3 async/await 支持

- `analysis_expression()` 中处理 `AwaitExpression` → 提取 argument（通常是 CallExpression）
- `VariableDeclaration` init 为 `AwaitExpression` → 同上
- `TryStatement` → 进入 try 块分析（async/await 常配合 try-catch）

### 9.4 回调函数追踪

```javascript
fs.readFile(path, function(data) {
    res.write(data);  // sink
});
```

`analysis_callexpression` 在 `vul_lineno > call.start.line` 时遍历 arguments 查找 `FunctionExpression`/`ArrowFunctionExpression` 类型的回调，构造 `callback_back_node` 递归进入。

---

## 10. 追踪缓存策略

JS 引擎的缓存使用与 PHP 引擎一致的双层策略：

**读取缓存**（parameters_back 入口）：
```python
cached = _trace_cache.get(file_path, param_name, int(lineno))
if cached is not None:
    return cached
```

**写入缓存**（deep_parameters_back 出口）：
```python
if lineno and file_path and isinstance(is_co, int) and is_co in (-1, 1, 2):
    _trace_cache.put(file_path, param_str, int(lineno), (is_co, cp, expr_lineno))
```

**只缓存确定性结果**（-1/1/2），跳过中间状态（3/4）和 deps 返回值。这避免了将"未确定"的错误结论缓存导致漏报。

---

## 11. 结果判定与输出

### 11.1 set_scan_results (line 2197)

```python
result = {
    'code': is_co,            # 可控性代码
    'source': get_member_data(cp),  # 污点源
    'source_lineno': expr_lineno,   # 源行号
    'sink': sink,             # sink 函数名
    'sink_param:': get_member_data(param),  # sink 参数
    'sink_lineno': vul_lineno,       # sink 行号
    "chain": scan_chain,      # 完整回溯链
}
```

**结果过滤**：
- `code in (1, 2, 3)` → 添加到结果
- `code == -1` → 仅在没有其他结果时保留（分支约束阻断结果，低优先级）
- `code == 4` → 不添加（新函数规则，留给后续扫描使用）

### 11.2 scan_chain 追踪记录格式

scan_chain 中的每个条目是一个元组 `(type, description, file_path, lineno)`：

| type | 含义 | 触发位置 |
|------|------|----------|
| `'start'` | 分析开始 | scan_parser 初始化 |
| `'NewFind'` | 找到 sink 参数 | analysis_params |
| `'Assignment'` | 变量赋值 `x=y` | parameters_back |
| `'NewParam'` | 对象合并新参数 | parameters_back |
| `'NewFunction'` | 新函数规则生成 | 多处 |
| `'Function Define'` | 回溯到函数定义 | function_call_back |
| `'TmpFunctionCall'` | 闭包调用 | function_call_back |
| `'TmpFunction'` | 闭包参数映射 | function_call_back |
| `'ObjectProperty'` | 对象属性查找 | member_back |
| `'ObjectSelfAss'` | 对象自引用 | member_back |
| `'ReverseParam'` | reverse() 结果反转 | function_call_back |
| `'CallExprCallee'` | 调用 callee 追踪 | parameters_back |
| `'ThisProp'` | this 属性映射 | parameters_back |

---

## 12. 完整回溯链路图

```
scan_parser()
  │
  ├─ _init_function_summaries()     ← 加载函数摘要缓存
  ├─ _trace_cache.clear()
  │
  └─ for func in sensitive_func:
       │
       └─ analysis(all_nodes, func, back_node, vul_lineno)
            │
            ├─ [前向扫描，构建 back_node]
            │  按 node.type 分发：
            │  ├── ExpressionStatement → analysis_expression()
            │  │    └─ CallExpression → analysis_callexpression()
            │  │         ├─ eval/setTimeout → analysis_params(is_eval=True)
            │  │         ├─ FunctionExpression → 递归进入函数体
            │  │         ├─ Class method call → 更新 _this_prop_map
            │  │         └─ 其他 → analysis_params()
            │  │              │
            │  │              └─ get_param_list(arguments)
            │  │                 └─ for param:
            │  │                      └─ deep_parameters_back(param, back_node)
            │  │                           └─ parameters_back(param, back_node)
            │  │                                │
            │  │                                ├─ [缓存检查]
            │  │                                ├─ is_controllable()
            │  │                                ├─ [this 属性映射]
            │  │                                │
            │  │                                ├─ MemberExpression → member_back()
            │  │                                │    ├─ parameters_back(object)
            │  │                                │    └─ [对象属性查找]
            │  │                                │
            │  │                                ├─ NewExpression → new_back()
            │  │                                │    └─ [prototype 追踪]
            │  │                                │
            │  │                                ├─ CallExpression → function_call_back()
            │  │                                │    ├─ [闭包处理]
            │  │                                │    ├─ [内置知识库]
            │  │                                │    ├─ [函数摘要]
            │  │                                │    │   └─ _judge_from_summary_js()
            │  │                                │    └─ [函数定义查找]
            │  │                                │         └─ function_back()
            │  │                                │              ├─ [内置知识库 passthrough]
            │  │                                │              ├─ [return 表达式分析]
            │  │                                │              │   └─ _collect_js_var_names()
            │  │                                │              │      → deps 机制
            │  │                                │              └─ [形参匹配]
            │  │                                │
            │  │                                └─ 变量赋值追踪
            │  │                                     ├─ VariableDeclarator
            │  │                                     ├─ ExpressionStatement
            │  │                                     ├─ [三元运算符分支约束]
            │  │                                     └─ [BinaryExpression + 拆分]
            │  │
            │  ├── ClassDeclaration → [两阶段分析]
            │  │    ├─ Phase 1: 构建 _this_prop_map
            │  │    ├─ Phase 1.5: _resolve_class_method_calls()
            │  │    └─ Phase 2: 递归进入 sink 所在方法体
            │  │
            │   └── [VariableDeclaration / IfStatement / Switch / While / Try]
            │
            └─ → 最终判定: set_scan_results()
                 ├─ code=1 → 漏洞确认（用户可控）
                 ├─ code=2 → 已修复
                 ├─ code=3 → 未确定（仍可能有风险）
                 └─ code=-1 → 不可控（仅在没有其他结果时保留）
```

---

## 13. JS 引擎 vs PHP 引擎设计对比

| 维度 | JS 引擎 | PHP 引擎 |
|------|---------|----------|
| 解析器 | esprima (Python binding) | lphply (PLY-based) |
| 可控源匹配 | substring 匹配（`in`） | 精确匹配（`==`） |
| 函数回溯 | deps 机制（返回变量名列表，外层映射） | _parameters_back_impl 进入函数体 |
| 对象传递 | prototype 链 + eval method + 对象合并 | `$obj->method` 调用链 |
| Class 支持 | ES6 Class + this 属性映射（两阶段） | PHP Class 方法追踪 |
| 跨文件追踪 | 无（单文件分析） | include/require 跨文件 |
| 闭包支持 | IIFE 参数映射 | 无 |
| async/await | await + try-catch 支持 | 无 |
| 默认可控源 | 30+ 项（浏览器/扩展/Node.js） | 11 项（PHP 超全局变量） |
| 内置知识库 | 独立 `builtin_knowledge.py`（100+ 函数） | 内嵌 `is_controllable` |
| 函数摘要 | `summary_generator.py` + `_judge_from_summary_js` | `_judge_from_summary_php` |
| 递归深度限制 | 20 层 | 无显式限制 |
| 追踪缓存 | TraceCache("javascript") | TraceCache() |
| 特殊函数 | eval/setTimeout | 无 |

---

## 14. 已知局限与设计权衡

1. **substring 匹配的误报风险**：`req.body.` 会匹配任何以 `req.body.` 开头的属性，但也会匹配 `req.body_extra` 等非预期变量
2. **单文件分析**：JS 引擎没有类似 PHP include/require 的跨文件追踪能力，对于 `import`/`export` 的模块系统支持有限
3. **deps 机制的精度**：函数回溯只分析 return 语句，忽略函数体中间的变量赋值和条件分支，可能错过复杂的内部控制流
4. **对象合并（set_original_object）的保守性**：对象传递场景中，如果右值为 MemberExpression，会尝试保留原始对象信息，但实现较为粗糙
5. **switch 语句**：analysis 中处理了 switch-case 遍历，但回溯路径中没有专门的 switch 分支约束提取（不同于 if/三元运算符）
