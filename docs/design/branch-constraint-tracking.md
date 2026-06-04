# 分支条件约束追踪 — 设计方案

## 1. 现状问题

### 1.1 所有语言引擎的共同盲区

当前各语言引擎的 `parameters_back` 在遇到 `if/elseif/else` 分支时，会**分别递归进入各分支体**做变量回溯，但**完全忽略条件表达式本身**。

```python
# PHP 引擎（parser.py L1532-1607）的伪代码
if isinstance(node, php.If):
    # 递归进入 if body
    is_co, cp, expr_lineno = parameters_back(param, if_nodes, ...)
    # 递归进入 elseif
    ...
    # 递归进入 else
    ...
    # 合并：任一分支返回 code=1 就认为可控
    # ❌ 完全忽略 node.expr 条件表达式
```

同样的问题存在于：
- **Python**（parser.py L734-748）：递归进入 `stmt.body` 和 `stmt.orelse`，忽略 `stmt.test`
- **JavaScript**（parser.py L1633-1657）：递归进入 `consequent` 和 `alternate`，忽略 `test`
- **Go**：tree-sitter 方式处理，同样忽略条件
- **Java**（parser.py L303-304）：`_flatten_statements` 展开后同样丢失条件信息

### 1.2 导致的误报场景

**场景 A：isset 守卫**
```php
function query($id) {
    if (isset($_GET['id'])) {
        $id = $_GET['id'];
    } else {
        $id = 1;  // 安全默认值
    }
    // $id 在 if 分支可控，在 else 分支不可控
    // 但当前引擎认为 if 分支可控就报漏洞
    $result = db::query("SELECT * FROM users WHERE id=" . $id);
}
```
当前行为：`$id` 在 if body 中追踪到 `$_GET['id']`，报告 SQL 注入。
期望行为：需要考虑 $id 在 else 分支已被赋值为字面量 1，不能确定 $id 一定可控。

**场景 B：类型守卫**
```python
def process(cmd):
    if isinstance(cmd, str):
        result = os.system(cmd)  # 真正危险
    else:
        cmd = str(cmd)  # 转换后不一定是原始输入
```
当前行为：直接在 if body 内找到可控 cmd，报告命令注入。
期望行为：正确识别 cmd 确实在 if body 内可控，这是真正的漏洞，不应误消。

**场景 C：条件赋值**
```javascript
function render(input) {
    var data;
    if (input.type === 'admin') {
        data = input.name;  // 来自用户输入
    } else {
        data = 'guest';
    }
    document.write(data);  // 并非一定可控
}
```

### 1.3 核心矛盾

- **场景 A/C** 是误报：变量在某些分支可控但在其他分支不可控，应判定为"不确定"而非"可控"
- **场景 B** 是真阳性：变量在 if body 内确实可控，sink 也在同一分支内

区别在于：**sink 所在的分支是否与可控来源在同一分支**。当前引擎不区分这一点。

---

## 2. 核心设计

### 2.1 设计原则

1. **不做预扫描，在回溯中携带约束**：不单独构建 constraint_map，而是让 `parameters_back` 在递归进入分支时**传入当前分支的约束集合**
2. **约束只影响"不在本分支内"的判定**：如果 sink 和 source 在同一分支体内，约束不影响判定
3. **最小侵入**：只给 `parameters_back` 加一个可选参数 `branch_constraints`，默认为空列表（无约束），不影响现有逻辑
4. **跨语言统一接口**：所有语言引擎使用相同的数据结构定义

### 2.2 BranchConstraint 数据结构

```python
class BranchConstraint:
    """单个条件约束"""
    var_name: str       # 被约束的变量名，如 "input", "$_GET['id']"
    op: str             # 操作符：==, ===, !=, !==, isset, !isset, in, not in
    value: any          # 常量值（字符串/数字/None），或 None 表示"存在性"
    
    def negate(self) -> 'BranchConstraint':
        """取反约束，用于 else/else if 分支"""
        neg_map = {
            '==': '!=', '===': '!==',
            '!=': '==', '!==': '===',
            'isset': '!isset', '!isset': 'isset',
            'in': 'not in', 'not in': 'in',
        }
        return BranchConstraint(
            var_name=self.var_name,
            op=neg_map.get(self.op, self.op),
            value=self.value
        )
```

### 2.3 BranchContext 上下文管理器

```python
class BranchContext:
    """管理当前分支的约束集合"""
    
    def __init__(self, constraints: list[BranchConstraint] = None):
        self.constraints = constraints or []
    
    def merge(self, new_constraints: list[BranchConstraint]) -> 'BranchContext':
        """合并新约束（进入嵌套分支时）"""
        return BranchContext(self.constraints + new_constraints)
    
    def applies_to(self, var_name: str) -> bool:
        """检查是否有约束涉及该变量"""
        return any(c.var_name == var_name for c in self.constraints)
    
    def get_constraints_for(self, var_name: str) -> list[BranchConstraint]:
        """获取涉及指定变量的所有约束"""
        return [c for c in self.constraints if c.var_name == var_name]
```

### 2.4 extract_constraints_from_expr

从条件表达式中提取约束列表。需要各语言引擎分别实现，因为 AST 节点类型不同。

```python
# PHP 实现
def extract_constraints_from_php_expr(expr) -> list[BranchConstraint]:
    """
    从 PHP 条件表达式中提取 BranchConstraint 列表
    
    支持的模式：
    - isset($var)           → [BranchConstraint(var_name="$var", op="isset")]
    - empty($var)           → [BranchConstraint(var_name="$var", op="!isset")]
    - $var === value         → [BranchConstraint(var_name="$var", op="===", value=value)]
    - $var != value          → [BranchConstraint(var_name="$var", op="!=", value=value)]
    - is_string($var)        → [BranchConstraint(var_name="$var", op="==", value="__type_string")]  # 类型约束
    - !isset($var)           → [BranchConstraint(var_name="$var", op="!isset")]
    """
    constraints = []
    if isinstance(expr, php.FunctionCall):
        fname = get_function_name(expr)
        if fname in ('isset', 'empty'):
            op = 'isset' if fname == 'isset' else '!isset'
            for arg in expr.params:
                if isinstance(arg, php.Variable):
                    constraints.append(BranchConstraint(var_name=arg.name, op=op))
    elif isinstance(expr, php.BinaryOp):
        # $var == value, $var === value, etc.
        ...
    elif isinstance(expr, php.BooleanNot):
        # !isset(...) 等
        inner = extract_constraints_from_php_expr(expr.expr)
        return [c.negate() for c in inner]
    elif isinstance(expr, php.LogicalOp):
        # A && B → 两个约束都要满足
        left = extract_constraints_from_php_expr(expr.left)
        right = extract_constraints_from_php_expr(expr.right)
        return left + right
    elif isinstance(expr, php.LogicalOr):
        # A || B → 不能同时保证（简化处理：忽略 or 条件）
        return []
    return constraints
```

### 2.5 修改 parameters_back 的分支处理

以 PHP 为例，核心改动在 `_parameters_back_impl` 的 `php.If` 处理块（L1532-1607）：

```python
elif isinstance(node, php.If):
    # ===== 新增：提取 if 条件的约束 =====
    if_constraints = extract_constraints_from_php_expr(node.expr)
    else_constraints = [c.negate() for c in if_constraints]
    
    # ===== if 分支：传入 if 约束 =====
    if_ctx = branch_ctx.merge(if_constraints) if branch_ctx else BranchContext(if_constraints)
    is_co, cp, expr_lineno = parameters_back(
        param, if_nodes, ..., 
        branch_ctx=if_ctx  # 新增参数
    )
    ...
    
    # ===== elseif 分支 =====
    for node_elseifs_node in node.elseifs:
        elif_constraints = extract_constraints_from_php_expr(node_elseifs_node.expr)
        # elseif 的隐含约束 = else_constraints AND elif_constraints
        combined = else_constraints + elif_constraints
        elif_ctx = branch_ctx.merge(combined) if branch_ctx else BranchContext(combined)
        
        is_co, cp, expr_lineno = parameters_back(
            param, elif_nodes, ...,
            branch_ctx=elif_ctx  # 新增参数
        )
    
    # ===== else 分支：传入否定约束 =====
    else_ctx = branch_ctx.merge(else_constraints) if branch_ctx else BranchContext(else_constraints)
    is_co, cp, expr_lineno = parameters_back(
        param, else_nodes, ...,
        branch_ctx=else_ctx  # 新增参数
    )
```

### 2.6 约束如何影响可控性判定

约束只在**变量被追踪到分支外部**时才起作用。判定逻辑：

```
当 parameters_back 返回 is_co=1（可控）时：
  1. 检查 source（可控来源）是否在当前分支体内
     - 如果 source.lineno 在当前 if/else/elseif 的行号范围内 → 真阳性，不受约束影响
  2. 如果 source 来自分支外部（更早的赋值/函数参数）：
     - 检查 branch_ctx 中是否有与该变量相关的约束
     - 如果约束表明变量被条件保护（如 isset → 变量存在），则检查是否合理
  3. 关键：如果变量在**不同分支有不同赋值**，当前逻辑（is_co==3 表示变量被修改）已有处理
```

**简化的判定规则**：

```python
def apply_branch_constraints(is_co, cp, branch_ctx, current_branch_range):
    """
    在 parameters_back 返回结果后，应用分支约束。
    
    核心逻辑：
    - is_co == 1（可控）且 source 在当前分支内 → 不修改（真阳性）
    - is_co == 1（可控）但 source 来自分支外 → 需要考虑约束
    - is_co == 3（变量被分支修改）→ 已有处理逻辑，不额外修改
    - is_co == -1（不可控）→ 不修改
    """
    if is_co != 1 or not branch_ctx or not branch_ctx.constraints:
        return is_co, cp
    
    # is_co == 1 且有分支约束
    # 需要检查：这个"可控"是否在当前分支内被条件保护
    # 如果变量的来源在分支外，且分支约束说明该分支要求特定条件
    # 那么这个可控性是有条件的
    
    # 简化：如果有约束存在，将确定性的 1 降级为 3（不确定）
    # 让上层（合并逻辑）决定是否报告
    return 3, cp
```

> **重要设计决策**：第一阶段采用保守策略 — 有约束时将 `is_co=1` 降级为 `is_co=3`（变量被修改/不确定），而非直接判为不可控。这样可以避免误消真阳性，后续可以通过规则 main() 做精确二次筛选。

---

## 3. 各语言实现差异

### 3.1 实现策略对比

| 方面 | PHP | Python | JavaScript | Go | Java |
|------|-----|--------|------------|----|----|
| AST 节点类型 | `php.If`, `php.ElseIf` | `ast.If` | `node.type == "IfStatement"` | tree-sitter `if_statement` | `javalang.tree.IfStatement` |
| 条件字段 | `node.expr` | `stmt.test` | `node.test` | `node.condition` | `stmt.condition` |
| 分支体字段 | `node.node`, `node.elseifs`, `node.else_` | `stmt.body`, `stmt.orelse` | `node.consequent`, `node.alternate` | `node.consequence`, `node.alternative` | `stmt.then_statement`, `stmt.else_statement` |
| extract 实现 | `extract_constraints_from_php_expr` | `extract_constraints_from_py_expr` | `extract_constraints_from_js_expr` | `extract_constraints_from_go_expr` | `extract_constraints_from_java_expr` |

### 3.2 各语言 extract 函数的重点

**PHP**：
- `isset()` / `empty()` → 存在性约束
- `$var ===/== value` → 等值约束
- `is_string()` / `is_int()` 等 → 类型约束（简化处理）

**Python**：
- `isinstance(x, type)` → 类型约束
- `x is None` / `x is not None` → 等值约束
- `x in list` → 成员约束
- `hasattr(x, attr)` → 属性存在约束

**JavaScript**：
- `typeof x === "string"` → 类型约束
- `x === value` → 等值约束
- `Array.isArray(x)` → 类型约束
- `x !== null` / `x !== undefined` → 非空约束

**Go**：
- `err != nil` → 错误检查（对安全影响大）
- `x == value` → 等值约束
- `len(x) > 0` → 长度约束

**Java**：
- `x != null` → 非空约束
- `x instanceof Type` → 类型约束
- `x.equals(value)` → 等值约束

---

## 4. 实施计划

### Phase 1：数据结构与 PHP 实现（最复杂，PHP 分支结构最完整）

1. 在 `core/core_engine/` 下新建 `branch_constraint.py`（公共模块）
   - `BranchConstraint` 数据类
   - `BranchContext` 上下文管理器
   - `negate()` 方法
2. PHP `extract_constraints_from_php_expr` 实现
3. PHP `_parameters_back_impl` 改造：`branch_ctx` 参数
4. 编写 PHP 测试用例（场景 A/C 的误报消除）

### Phase 2：Python 实现

1. `extract_constraints_from_py_expr` 实现
2. Python `_trace_in_stmts` 的 `ast.If` 处理改造
3. 测试用例

### Phase 3：JavaScript 实现

1. `extract_constraints_from_js_expr` 实现
2. JS `parameters_back` 的 `IfStatement` 处理改造
3. 测试用例

### Phase 4：Go 实现

1. `extract_constraints_from_go_expr` 实现
2. Go 引擎 if 处理改造
3. 测试用例

### Phase 5：Java 实现

1. `extract_constraints_from_java_expr` 实现
2. Java 引擎 `_flatten_statements` 改造（当前 Java 展开分支时丢失了分支信息，需要改为结构化处理）
3. 测试用例

---

## 5. 开放问题

1. **约束传播深度**：嵌套 if（if 内 if）如何传播约束？当前设计用 `merge()` 累积，嵌套过深可能约束过多
2. **循环中的约束**：`while (condition)` 的条件是否也要提取？循环体的约束比 if 更复杂
3. **约束冲突**：外层 `isset($x)` 进入 if，内层 `!isset($x)` 又进入 if → 逻辑上不可能，如何处理？
4. **类型约束的判定**：`is_string($cmd)` 之后 `$cmd` 仍然来自用户输入 → 类型约束对可控性无影响。类型约束只在变量类型决定是否可注入时才有意义（如 Java 的类型转换）
5. **约束的保守性**：第一阶段采用"降级为不确定"策略，是否需要更精确的约束求解？
6. **switch 语句**：Java/PHP/JS 的 switch-case 也涉及分支约束，是否纳入第一阶段？

## 6. 与函数摘要系统的关系

函数摘要系统（`docs/design/function-summary.md`）记录的是**函数级数据流事实**，而分支约束追踪是**语句级控制流事实**。两者互补：

- 函数摘要：`f()` 返回 `$_GET['id']` → 来源可控
- 分支约束：但在调用 `f()` 的地方有 `if (isset(...))` 保护

未来可以结合：在函数摘要的消费端加入分支约束检查。
