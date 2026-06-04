# Kunlun-M 函数摘要系统设计文档

## 1. 背景与动机

### 1.1 现状问题

当前 Kunlun-M 的 AST 分析流程中，每次遇到函数调用都需要做一次完整的反向追踪（`function_back` / `_trace_function_return`），存在以下问题：

1. **重复分析**：同一个函数被不同 sink 参数追踪时，会被重复分析多次
2. **缓存粒度不对**：运行时缓存 `_trace_cache` 的 key 是 `(file, var_name, lineno)`，换个变量名就 miss
3. **知识库覆盖有限**：内置知识库（`builtin_knowledge.py`）只覆盖标准库/框架函数，用户自定义函数完全不覆盖
4. **知识库与 AST 分析脱节**：要么走知识库快捷路径，要么走完整 AST 分析，两者之间没有衔接

### 1.2 解决思路

在 AST 分析之前增加一个**函数摘要生成**阶段，预先对所有函数/方法做一次数据流分析，生成函数摘要。AST 回溯分析阶段改为消费摘要，而非重复做 AST 分析。

---

## 2. 核心原则

### 2.1 摘要只记录数据流事实，不做安全判定

```
✅ 记录：返回值来自 request.GET.get（数据流事实）
❌ 不记录：返回值可控（安全判定）
```

"可不可控"取决于规则配置，同一份摘要在不同规则下可以得出不同判定结果。

### 2.2 摘要是函数的固有属性

只要函数代码不变，摘要就不变。摘要可以跨扫描任务复用。

### 2.3 初始化阶段从 return 反向追踪

对每个函数，从 `return` 语句出发，反向追踪返回值的数据流链，直到碰到内置方法、形参、或全局变量为止。

---

## 3. 数据结构设计

### 3.1 单条返回值数据流

```json
{
    "order": 0,
    "return_index": 0,
    "origin": "request.GET.get",
    "origin_type": "call",
    "dep_params": [],
    "path": [
        {"node": "request.GET.get", "type": "call", "line": 20}
    ]
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `order` | int | 同一个 return_index 下的多条数据流路径，从 0 递增 |
| `return_index` | int | 多返回值中的索引（0-indexed）。单返回值语言（PHP/JS/Java）固定为 0 |
| `origin` | string | 最终来源的标识（方法名、变量名、字面量等） |
| `origin_type` | string enum | 来源类型，见下表 |
| `dep_params` | list[int] | 数据流依赖哪些形参（按参数索引，0-indexed） |
| `path` | list | 从 return 到 origin 的中间节点路径（可选，用于 chain 展示） |

### 3.2 origin_type 枚举

| 值 | 含义 | 示例 |
|----|------|------|
| `call` | 方法调用 | `request.GET.get`, `db.Query`, `sanitize` |
| `param` | 直接来自形参 | 函数参数 `data` |
| `global` | 全局变量/内置 source | `$_GET`, `request`, `r.URL.Query()` |
| `literal` | 字面量 | `"hello"`, `42`, `nil`, `None` |
| `unknown` | 无法确定来源 | 复杂表达式、多来源拼接等 |

### 3.3 单个函数的完整摘要

```json
{
    "name": "getUser",
    "params": ["id", "db"],
    "line_range": [10, 25],
    "return_flow": [
        {
            "order": 0,
            "return_index": 0,
            "origin": "db.Query",
            "origin_type": "call",
            "dep_params": [0, 1]
        },
        {
            "order": 0,
            "return_index": 1,
            "origin": "nil",
            "origin_type": "literal",
            "dep_params": []
        }
    ]
}
```

### 3.4 多 return 路径的函数

```python
def process(data, flag):
    if flag:
        return request.GET.get('cmd')
    return sanitize(data)
```

```json
{
    "name": "process",
    "params": ["data", "flag"],
    "line_range": [10, 15],
    "return_flow": [
        {
            "order": 0,
            "return_index": 0,
            "origin": "request.GET.get",
            "origin_type": "call",
            "dep_params": []
        },
        {
            "order": 1,
            "return_index": 0,
            "origin": "sanitize",
            "origin_type": "call",
            "dep_params": [0]
        }
    ]
}
```

### 3.5 单文件摘要

```json
{
    "file": "views.py",
    "content_hash": "sha256:abc123...",
    "functions": [
        { "...单个函数摘要..." },
        { "...单个函数摘要..." }
    ]
}
```

---

## 4. 持久化方案

### 4.1 目录结构

```
<target_path>/.kunlun_cache/
├── index.json                        # 索引：文件路径 → content_hash
├── summaries/
│   ├── a1b2c3d4e5f6.json             # 文件级函数摘要
│   ├── f7e8d9c0b1a2.json
│   └── ...
```

### 4.2 缓存失效策略

扫描开始时：

1. 计算目标文件 `content_hash`（SHA-256）
2. 读取 `index.json`，对比 hash
3. hash 没变 → 直接加载 `summaries/*.json`
4. hash 变了 → 只对该文件重新生成摘要，更新 JSON

### 4.3 复用场景

| 场景 | 处理方式 |
|------|---------|
| 同项目重复扫描 | hash 不变，直接复用，秒级启动 |
| 只改了几个文件 | 只重新生成变更文件的摘要 |
| 单文件扫描 | 仍加载依赖文件的摘要（跨文件追踪需要） |
| 第三方库 | 可预生成摘要分发 |
| 清理 | 删掉 `.kunlun_cache/` 即可，下次自动重建 |

### 4.4 .gitignore

`.kunlun_cache/` 是本地构建产物，不入版本控制。

---

## 5. 扫描流程

### 5.1 阶段一：预处理（函数摘要生成）

```
遍历所有目标文件
    → 解析 AST
    → 对每个函数/方法：
        → 找到所有 return 语句
        → 从 return 值反向追踪数据流
        → 遇到自定义方法 → 递归查已有摘要（或递归分析）
        → 碰到内置方法 / 形参 / 全局变量 / 字面量 → 终止
        → 记录 return_flow
    → 生成单文件摘要 JSON
    → 对比 content_hash，写入缓存
```

### 5.2 阶段二：AST 回溯分析（消费摘要）

```
grep 匹配 → scan_parser → 反向追踪变量
    → 遇到函数调用
        → 查函数摘要
        → return_flow 中每条路径独立判定：
            → origin_type == "param"：
                → 追踪对应的实参（dep_params 指定的参数索引）
            → origin_type == "call"：
                → 查内置知识库判定（source/repair/safe）
            → origin_type == "global"：
                → 检查是否在当前规则的 source 列表中
            → origin_type == "literal"：
                → 不可控
        → 只要任意一条路径可控，就认为返回值可控
```

---

## 6. 多语言差异

| 特性 | PHP | Python | JavaScript | Go | Java |
|------|-----|--------|------------|----|------|
| 多返回值 | ❌ | ✅ tuple | ❌ | ✅ | ❌ |
| 需要记录 return_index | ❌ (固定 0) | ✅ | ❌ (固定 0) | ✅ | ❌ (固定 0) |
| 函数定义语法 | `function name()` | `def name()` | `function name()` | `func name()` | 方法声明 |
| 类方法 | ✅ | ✅ self | ✅ this | ✅ receiver | ✅ this |
| 闭包/匿名函数 | ✅ | ✅ lambda | ✅ arrow func | ✅ func literal | ✅ lambda |

---

## 7. 与现有系统的关系

### 7.1 替代关系

| 现有机制 | 新方案 | 说明 |
|---------|--------|------|
| `_trace_cache` (运行时缓存) | 函数摘要 | 粒度从"变量在某一行的追踪结果"提升为"函数级数据流摘要" |
| `builtin_knowledge.py` (内置知识库) | **保留**，作为摘要生成和查询的辅助 | 内置方法不需要生成摘要，直接查知识库 |
| `function_back` / `_trace_function_return` | **简化**，改为消费摘要 | 不再重复做 AST 分析 |

### 7.2 保留关系

| 机制 | 说明 |
|------|------|
| `builtin_knowledge.py` | 内置方法的知识库，摘要生成时的终止条件之一 |
| `GO_CONTROLLED_SOURCES` 等 | 各语言的可控源列表，`origin_type == "global"` 判定时使用 |
| `is_controllable()` / `_is_controllable_source()` | 查询摘要时的安全判定函数 |
| `check_comment` (grep 层) | 不受影响 |

---

## 8. 实施计划

### Phase 1: 基础框架

1. 定义函数摘要数据结构（Python dataclass）
2. 实现缓存管理器（index.json + summaries/*.json 的读写和失效判断）
3. 单个引擎（Go）的摘要生成器

### Phase 2: 摘要生成

4. Go 引擎：从 return 反向追踪，生成 return_flow
5. 处理多返回值（return_index）
6. 处理多 return 路径（order）
7. 递归分析自定义方法调用

### Phase 3: 消费摘要

8. 修改 `scan_parser`：遇到函数调用时查摘要
9. 修改 `function_back_go`：简化为摘要查询
10. 修改 `_analyze_return_deps_go`：简化为摘要查询

### Phase 4: 跨语言推广

11. Python 引擎适配
12. JavaScript 引擎适配
13. PHP 引擎适配
14. Java 引擎评估（前向分析架构差异较大）

---

## 9. 开放问题

1. **递归深度限制**：摘要生成时遇到自定义方法递归分析，需要设深度上限（建议 5 层）
2. **循环引用**：A 调 B，B 调 A，需要去重（记录已分析函数集合）
3. **接口/多态**：`interface{}` 的方法调用在摘要中如何表达？
4. **全局变量追踪**：函数体内读取全局变量（非形参、非 source），是否需要在摘要中体现？
5. **第三方库摘要分发**：是否需要支持预生成 `django_summaries.json` 等第三方库摘要？
