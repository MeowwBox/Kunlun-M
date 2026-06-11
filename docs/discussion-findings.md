# 架构分析讨论记录

> 讨论日期：2026-06-12
> 讨论原则：不动代码，先逐点讨论→纠正误解→记录结论文档→讨论完所有部分后再统一规划和开发

---

## 问题 1：跨文件分析 & 回溯架构

### 1.1 跨文件分析的正确理解

**纠正之前的错误认知：** 跨文件分析不是"纯 grep 文本匹配"。grep 只是入口定位步骤，后续都跟着 AST 级分析。

跨文件分析有两层机制：

**机制 A：include/import 路径解析 → 加载被引用文件的 AST → 递归回溯**
- PHP `deep_parameters_back`：遇到 include/require → `get_filename` 解析路径 → `ast_object.get_nodes()` 加载新文件 AST → 继续追踪
- JS `_try_cross_file_trace_js`：`_parse_js_imports` 构建 import_map → 单文件分析未检出时 → 用 import_map 找被 import 文件 → 加载 AST → 检查函数体内 sink + 参数可控性
- Python：`_parse_imports` 已解析 import_map，但返回值未传入回溯链路（见 1.3 具体问题）
- Go：`_parse_go_imports` 已定义完整逻辑（含本地 vs 外部包判定），但从未被调用

**机制 B：全局函数定义索引**
- C `_build_func_def_index_cross_file`：扫描所有 C/C++ 文件建立 `(file_path, func_name) → (params, body, line_range)` 索引
- Java `_build_global_method_map`：扫描所有 Java 文件建立 `(method_name, param_count) → [(tree, method_node, filepath)]` 索引
- Go `_build_func_def_index_cross_file`：同 C 模式

### 1.2 回溯分析的架构分层

回溯分析追踪 sink 参数来源，正确判定链路：

```
可控源检查 → 修复函数检查 → 内置知识库(builtin) → 函数摘要(summary) → 未确认
```

**注意：回溯分析不会进入函数体递归追踪，也不会触发 NewCore。** 遇到函数调用返回值时，用知识库和摘要判定就够了。

### 1.3 NewCore 的正确触发条件

NewCore 是**独立的机制**，和回溯分析不在一条路上。

**触发条件：回溯追踪 sink 参数，数据流最终到达函数形参** → 说明形参直通 sink → 该函数本身也是 sink → 生成新规则重新扫描。

**不触发 NewCore 的场景：** 回溯中遇到函数调用返回值，且 builtin 和 summary 都无法判定 → 应该返回"未确认"（code=3），不触发 NewCore。

### 1.4 具体问题清单

#### 问题 1.4.1（Go）：函数调用返回值场景缺少 summary + 错误触发 NewCore

- 位置：`core/core_engine/go/_ast_trace.py` `_trace_call_expr` 第 683-707 行
- 现状：`lookup_builtin` 有结果就用，没有 → 直接 `return (5, func_name)` 触发 NewCore
- 问题：
  1. **没有调用 `lookup_summary`**（已导入但从未使用）
  2. **未知函数直接标记 NewCore** — 正确做法是 builtin 和 summary 都没有时返回未确认
- 影响：项目中自定义的清洗函数（不在 builtin 中但可能在 summary 中）会被错误标记为 NewCore，导致误报

#### 问题 1.4.2（C）：函数调用返回值场景缺少 summary + 错误触发 NewCore

- 位置：`core/core_engine/c/parser.py` `_trace_call_expr_rhs` 第 1687-1718 行
- 现状：和 Go 完全相同的模式
- 问题：
  1. **`lookup_summary` 导入了但从未调用**
  2. **未知函数直接 `return (5, func_text)` 触发 NewCore**
- 影响：同 Go

#### 问题 1.4.3（Python）：import_map 解析了但未接入回溯链路

- 位置：`core/core_engine/python/parser.py`
  - `_parse_imports` 第 62-90 行
  - `scan_parser` 第 1818 行：`import_map = _parse_imports(tree, file_path)` 但之后无引用
  - `_find_function_def` 第 1216-1222 行：只在当前文件 AST 中搜索
- 现状：import_map 被解析后丢弃。`_find_function_def(tree, call_name)` 的 `tree` 是当前文件，import 的本地模块中定义的函数找不到
- 注意：Python 在函数调用返回值场景是正确处理了 builtin + summary 的（第 1304、1319 行），此问题仅影响引用递归分析（进入函数体追踪数据流）
- 对比：JS 有完整的 `_try_cross_file_trace_js`（第 401-564 行）实现了相同功能

#### 问题 1.4.4（Go）：`_parse_go_imports` 定义了但未调用

- 位置：`core/core_engine/go/parser.py` 第 641-729 行
- 现状：函数有完整的 import 解析和本地包判定逻辑，但从未被任何地方调用
- 分析（2026-06-12）：`_parse_go_imports` 的功能（import 别名 → 本地文件映射）已被 `_build_func_def_index_cross_file` 覆盖（全局扫描所有 Go 文件构建函数索引）。跨包调用不工作的**实际根因是 NewCore 的 grep 正则不支持包前缀**（如 `helpers.ExecuteCommand`），已在 commit c16ebe3 中修复。`_parse_go_imports` 属于冗余代码，可在后续清理中删除。

### 1.5 无问题的语言

| 语言 | 函数调用返回值场景 | 引用递归分析 | 形参 → NewCore |
|------|:--:|:--:|:--:|
| JS | ✅ builtin + summary 都有 | ✅ `_try_cross_file_trace_js` | ✅ |
| Java | ✅ builtin + summary 都有 | ✅ `_build_global_method_map` + 反向调用链 | ✅ |
| PHP | ✅ builtin + repair | ✅ `deep_parameters_back` include 加载 | ✅ |
| C | ✅ builtin（缺 summary） | ✅ 全局函数索引 | ✅ |
| Python | ✅ builtin + summary 都有 | ⚠️ 缺跨文件 import 接入 | ✅ |
| Go | ⚠️ 缺 summary + 错误 NewCore | ⚠️ import 解析未调用 | ✅ |

---

## 问题 3：逆向追踪架构局限性 & 知识库/摘要质量

### 3.1 逆向追踪模型评估

逆向追踪的基本模型：从 sink 参数出发，向上找赋值来源，逐层判定可控性。

之前列举的多个"局限"场景逐一分析后，确认**都不是架构级问题，而是知识库覆盖范围的问题**：

| 场景 | 之前认为的问题 | 实际情况 |
|------|--------------|---------|
| 多步间接赋值 `x=f(input) → y=g(x) → cmd=h(y)` | 逆向追踪跟不住 | builtin/summary 覆盖即可，知识覆盖问题 |
| 容器 append `arr.append(input) → system(arr[0])` | 逆向追踪盲区 | `list.append` 标记 passthrough 即可，builtin 覆盖 |
| 隐式数据流 `json.loads(request.body)` | 逆向追踪无法处理 | `json.loads` 标记 passthrough + `request.body` 可控，builtin 覆盖 |
| 闭包/回调 | 逆向追踪无法处理 | NewCore 机制覆盖 |
| 数据流汇聚 `cmd=input → cmd=sanitize(cmd)` | 需要正向传播 | 倒序遍历天然处理覆盖赋值 |

**逆向追踪架构本身没有天生局限。** 真正覆盖不了的只有多级属性链（`config.database.host = input`），出现概率极低。

### 3.2 知识库 & 函数摘要检查结果

对 6 个语言的 `builtin_knowledge.py` 和 `summary_generator.py` 做了全面检查。

#### 格式一致性 ✅

- 所有语言的 `lookup()` 返回格式统一：`{"passthrough": [...], "safe": bool, "param_flow": dict}`
- 所有语言的 `FunctionSummary`/`ReturnFlowItem` 共用 `core/core_engine/function_summary.py` dataclass
- 所有消费端字段访问和生成器输出格式匹配，无 key 名不匹配

#### 摘要生成逻辑 ✅

- 6 个语言都实现了两遍处理（第一遍注册摘要，第二遍递归展开）
- `_trace_dataflow` 都返回 `{origin, origin_type, dep_params, path}` 四字段
- AST 节点覆盖合理

#### 发现的问题

**已记录（问题 1.4 的补充）：**

- Go `lookup_summary` 未被调用（已在 1.4.1 记录）
- C `lookup_summary` 未被调用（已在 1.4.2 记录）
- Go `_ast_trace.py` 未检查 `param_flow`，只查了 `safe` 和 `passthrough`（低风险）

**新发现（低风险，不影响运行时）：**

| 语言 | 文件 | 问题 |
|------|------|------|
| JS | parser.py 第 973、1405 行 | `knowledge["safe"]` 直接下标访问，可能 KeyError（其他语言都用 `.get()`） |
| JS | builtin_knowledge.py | `sanitize` 重复定义（第 112 和 185 行） |
| Go | builtin_knowledge.py | `http.Request.FormValue` 和 `fmt.Errorf` 各重复两次 |
| Python | builtin_knowledge.py | 类型注解缺少 `param_flow`（运行时无影响） |

#### 结论

**知识库和摘要本身没有严重 bug。** 格式统一、生成逻辑正确、消费端匹配。Go/C 未调用 `lookup_summary` 是问题 1 中已记录的回溯链路缺失，不是知识库本身的问题。

---

## 问题 4：错误处理模式 — 静默异常吞没

### 4.1 全局共性问题（全部 6 语言）

#### E1：摘要初始化失败后永久阻止重试

全部 6 个语言的 `_init_function_summaries` 存在相同 bug：

```python
try:
    # ... 读取文件、生成摘要 ...
except Exception as e:
    logger.debug("摘要初始化失败: {}".format(e))  # debug 级别，正常扫描看不到
    _summaries_initialized = True  # ← 标记为已初始化，阻止后续重试
```

**影响**：如果扫描启动时某些文件不可读，摘要系统永久降级，跨函数分析完全失效（`lookup_summary` 永远返回空），且日志级别是 debug，正常运行时无任何提示。

**位置**：Python parser.py:1488、Go parser.py:242、C parser.py:1301、Java parser.py:1093、PHP parser.py:3295、JS parser.py:3238

### 4.2 高风险问题

| # | 语言 | 位置 | 问题 | 影响 |
|---|------|------|------|------|
| E2 | Go | parser.py:618 | `_parse_go_ast` 解析失败静默返回 None，无日志 | 整个文件所有 sink 零检出 |
| E3 | C | parser.py:132 | `_parse_c_ast` 同上 | 整个文件所有 sink 零检出 |
| E4 | Java | parser.py:1070,1075 | 裸 `except: pass` 吞含 SystemExit | 可能阻止进程正常退出 |
| E5 | Python | parser.py:1538 | `_is_controllable_global_variable` 静默返回 False | 可控变量误判安全，漏洞漏报 |
| E6 | PHP | parser.py:2353 | 裸 `except:` 在 `deep_parameters_back` Include 文件处理中 | Include 文件追踪跳过，漏洞漏报 |
| E7 | PHP+JS | 各 `_init_function_summaries` | `except Exception: pass` 文件读取失败 | 摘要初始化静默失败，跨函数追踪失效 |
| E8 | C | parser.py:2227 | `C_CONTROLLED_SOURCES` 全局可变列表被 `discover_sources` 修改 | 跨项目扫描时残留 source 产生误报 |

### 4.3 中等风险问题

| # | 语言 | 位置 | 问题 |
|---|------|------|------|
| E9 | Go | parser.py:1421 | `_text_trace_variable` 读取失败静默返回"不可控" |
| E10 | Java | parser.py:1537,1685 | 跨文件分析中单个文件失败静默跳过 |
| E11 | Java | parser.py:2198 | `find_sinks` 外层 `except: continue` 跳过整个文件 |
| E12 | PHP+JS | `scan_parser` | 全局变量 `scan_results` + 仅捕获 SyntaxError，异常导致状态泄漏 |

### 4.4 修复方向

- **E1（核心）**：去掉 `_summaries_initialized = True`，或将 `logger.debug` 改为 `logger.warning`
- **E2/E3**：AST 解析失败至少加 `logger.warning`，不应缓存失败的 None 结果
- **E4**：将裸 `except:` 改为 `except Exception:`
- **E8**：`C_CONTROLLED_SOURCES` 改为每次 `scan_parser` 调用时重建，不污染全局状态
- **E12**：`scan_parser` 的 `except SyntaxError` 改为 `except Exception`，或消除全局变量改用局部变量

---

## 问题 5：过滤函数模块（filter_functions）重构

### 5.1 现状问题

当前 sanitize/repair 判定分散在三个地方，效果差：

1. **`rules/tamper/demo.py` 等配置** — 手动维护，每语言仅 12 个左右
2. **`is_repair()` 函数** — 全部语言都是 `if rf in expr_str` 纯字符串包含匹配，误判和漏判严重
3. **`builtin_knowledge.py` 的 `safe: True`** — 精确匹配，但和 is_repair 重复且不一致

**核心问题**：字符串包含匹配太粗糙（`"intval" in "intval_expr"` 误判、`"escape" in "escape_route"` 误判），且维护分散。

### 5.2 设计方案：独立的 filter_functions 模块

将过滤函数判定逻辑从 tamper/is_repair/builtin 中独立出来，统一为一个 `filter_functions` 模块。

✅ **已完成（2026-06-12）**：三层体系已实现（commit ea6366f/d69e414/153d6b1）
- `core/filter_functions.py` — FilterFunctionRegistry，L1/L2/L3 数据结构 + 查询接口
- L1 (builtin): 从 IS_REPAIR_DEFAULT 加载，精确函数名 → CVI 集合
- L2 (summary): `_trace_function_return` 分析函数定义时自动继承 safe_for
- L3 (rule): CVI 规则通过 `extra_repair_functions` 属性追加
- 修复 Python/Go/C 的 `rf in expr_str` 字符串包含误判 → 精确匹配
- matcher 同时维护 `repair_functions` 列表（兼容现有 scan_parser 接口）

#### 三层加载机制

**第一层：内置表（builtin）**

从 `builtin_knowledge.py` 独立出来，结构类似但聚焦于过滤函数：

```python
FILTER_FUNCTIONS = {
    # PHP
    "htmlspecialchars": {"safe_for": [1000, 10001, 10002, 2000]},
    "escapeshellarg": {"safe_for": [1009, 1011]},
    "intval": {"safe_for": [1000, 10001, 10002, 1004, 1005, 1006]},
    "mysql_real_escape_string": {"safe_for": [1004, 1005, 1006]},
    # Python
    "html.escape": {"safe_for": [2000, 2006]},
    "markupsafe.escape": {"safe_for": [2000, 2006]},
    "shlex.quote": {"safe_for": [2000, 2001]},
    "int": {"safe_for": [2000, 2001]},
    # ...
}
```

特点：函数名 → CVI 编码列表的精确绑定。按函数维度组织，清晰可维护。

**第二层：函数摘要分析扩展（summary）**

在 `summary_generator` 两遍分析中，增加一步逻辑：

```
分析函数 return_flow 时：
  检查函数体内是否调用了 FILTER_FUNCTIONS 中的已知函数
  如果是 → 该函数继承被调用函数的 safe_for 设定
```

```python
# 示例：summary 分析发现
def my_escape(data):
    return html.escape(data)

# html.escape 在 FILTER_FUNCTIONS 中，safe_for = [2000, 2006]
# → my_escape 继承 safe_for = [2000, 2006]
# → 自动加入 FILTER_FUNCTIONS（标记 source="summary"）
```

关键：**不使用模糊匹配函数名**，完全基于 AST 调用链分析——函数内部调用了已知 filter 才继承，精确可靠。

已有 summary_generator 的两遍处理机制天然支持传递：如果 `wrapper` 调用了 `my_escape`，`my_escape` 调用了 `html.escape`，第二遍分析时 `wrapper` 也能通过 `my_escape` 间接继承。

**第三层：CVI 规则级自定义**

每个 CVI 规则保留入口，可以声明额外的过滤函数：

```python
class CVI_1011:
    vul_function = ['system', 'exec']
    extra_repair_functions = ['my_custom_clean', 'project_specific_sanitize']
```

加载时追加到 FILTER_FUNCTIONS 中，绑定当前 CVI。

#### 加载顺序

```
1. 内置表加载 → FILTER_FUNCTIONS 初始化
2. 摘要分析扩展 → 发现自定义 filter 函数，继承已有设定，追加到 FILTER_FUNCTIONS
3. CVI 规则追加 → extra_repair_functions 追加到 FILTER_FUNCTIONS
4. 扫描时 → 回溯分析中查 FILTER_FUNCTIONS，精确函数名匹配
```

#### 和现有模块的关系

- **替代**：`is_repair()` + `tamper/demo.py` 的 IS_REPAIR_DEFAULT 配置
- **保留**：`builtin_knowledge.py` 仍用于 passthrough/param_flow 等非 safe 判定
- **替代**：`builtin_knowledge.py` 中 `safe: True` 的条目移到 FILTER_FUNCTIONS
- **回溯分析**：各语言的 sanitize 检查统一调用 `filter_functions.is_safe(func_name, cvi)`

#### 后续扩展方向

- **项目级持久化**：摘要分析发现的候选 filter 可以存入项目配置（数据库表），下次扫描直接用
- **按漏洞类型分类**：CVI 可以声明所属 category（xss/sqli/cmdi/path_traversal 等），内置表也可以按 category 组织，减少重复列举 CVI 编号

---

## 问题 6：可控源发现 & tamper 模块改造

### 6.1 现状问题

当前可控源判定分散在两个并行体系：
1. **tamper 配置**（`rules/tamper/demo.py`）：IS_CONTROLLED_DEFAULT 硬编码，PHP 仅有 `["$_GET"]` 一个条目
2. **source_discovery**（各语言的 `source_discovery.py`）：框架检测 + AST 遍历，更全面但硬编码在各语言文件中

两个体系互不打通，tamper 的可控源列表过于单薄，source_discovery 的知识不可扩展。

### 6.2 tamper 模块改造方向

将 tamper 从简单的范例配置改造为**项目级配置 + 框架配置**的载体，具备框架自动识别能力。

#### 目录结构

```
tamper/
├── demo.py                    # 基础范例（保留）
├── php/
│   ├── laravel.py
│   ├── thinkphp.py
│   ├── symfony.py
│   └── ci.py
├── python/
│   ├── flask.py
│   ├── django.py
│   ├── fastapi.py
│   └── tornado.py
├── javascript/
│   ├── express.py
│   ├── koa.py
│   └── nestjs.py
├── java/
│   ├── spring.py
│   └── struts.py
├── go/
│   ├── gin.py
│   ├── echo.py
│   └── fiber.py
└── project_config.py          # 项目级自定义入口
```

#### 两步框架识别机制

**第一步：依赖文件匹配（纯数据声明，优先）**

每个框架配置文件声明 `DEPENDENCIES` 字典，扫描时统一解析对应语言的包管理器文件：

```python
# tamper/php/laravel.py

FRAMEWORK_NAME = "Laravel"

# 依赖声明，扫描时读取依赖文件自动匹配
# key: 包管理器名称，value: 依赖包名列表
DEPENDENCIES = {
    "composer": ["laravel/framework", "laravel/laravel"],
}
```

各语言的依赖文件对应关系：

| 语言 | 包管理器文件 | 解析字段 |
|------|------------|---------|
| PHP | `composer.json` | `require` |
| Python | `requirements.txt` / `pyproject.toml` | 行匹配 / `dependencies` |
| JavaScript | `package.json` | `dependencies` / `devDependencies` |
| Go | `go.mod` | `require` 块 |
| Java | `pom.xml` | `<dependencies>` |
| C | 无包管理器 → 直接走第二步 |

扫描时统一解析这些文件，对每个框架配置的 DEPENDENCIES 做字符串匹配。命中则加载该框架的配置。

**第二步：特征文件补正（detect 函数，第一步未命中时执行）**

```python
# tamper/php/laravel.py

def detect(project_dir, language='php'):
    """第一步没命中时的特征补正，返回 True 则加载"""
    # 检查特征文件/目录
    features = [
        'app/Http/Kernel.php',
        'app/Http/Middleware/',
        'routes/web.php',
    ]
    for path in features:
        if os.path.exists(os.path.join(project_dir, path)):
            return True
    return False
```

典型特征示例：

| 框架 | 特征文件/目录 |
|------|-------------|
| Django | `manage.py`, `wsgi.py`, `settings.py` |
| Flask | `app.py`, `templates/` 目录 |
| ThinkPHP | `thinkphp/` 目录, `tp5.php` 入口 |
| CodeIgniter | `application/controllers/`, `system/` 目录 |
| Express | `app.js` 中包含 `require('express')` |
| Spring Boot | `src/main/resources/application.properties` |

#### 框架配置文件的数据结构

每个框架配置文件在识别成功后加载以下字段：

```python
# tamper/php/laravel.py

FRAMEWORK_NAME = "Laravel"
DEPENDENCIES = {"composer": ["laravel/framework", "laravel/laravel"]}

def detect(project_dir, language='php'):
    """特征补正"""
    ...

# --- 以下配置仅在识别成功时加载 ---

# 框架特有的可控源（补充 source_discovery）
CONTROLLED_SOURCES = [
    "request()->input(", "request()->get(", "request()->post(",
    "$request->query(", "$request->input(",
    "Request::get(", "Request::input(",
]

# 框架特有的过滤函数（补充 filter_functions）
FILTER_FUNCTIONS = {
    "e()": {"safe_for": [1000, 2000]},
    "csrf_field()": {"safe_for": []},
}

# 框架特有的额外 sink
EXTRA_SINKS = [
    ("DB::raw", [1004, 1005]),
]
```

#### 加载流程

```
扫描项目
  → 识别语言
  → 遍历 tamper/{language}/*.py
    → 读取 DEPENDENCIES → 解析依赖文件 → 匹配
      → 命中 → 加载 CONTROLLED_SOURCES / FILTER_FUNCTIONS / EXTRA_SINKS
      → 未命中 → 调用 detect(project_dir)
        → True → 加载配置
        → False → 跳过
  → 运行 source_discovery → AST 遍历补充用户自定义 source
  → 加载项目级配置（project_config.py）→ 项目特有 override
  → 合并所有结果 → 注入扫描流程
```

#### 和 filter_functions（问题 5）的集成

框架配置中的 FILTER_FUNCTIONS 直接补充到 filter_functions 表，加载顺序：

```
1. builtin 内置表（标准库函数）
2. 框架配置（DEPENDENCIES/detect 命中后注入）← 新增
3. summary 分析扩展（AST 调用链继承）
4. CVI 规则自定义（extra_repair_functions）
5. 项目级配置
```

#### 和规则系统的类比

| 规则系统 | 框架系统 |
|---------|---------|
| 每个漏洞一个 CVI 文件 | 每个框架一个配置文件 |
| `main()` 做参数提取筛选 | `detect()` 做特征补正识别 |
| 匹配则进入 AST 分析 | 识别则加载框架配置 |
| 按语言目录组织 `rules/php/` | 按语言目录组织 `tamper/php/` |
| 自动发现（扫描 rules 目录） | 自动发现（扫描 tamper 目录） |

### 6.3 其他 source_discovery 问题

- **接口不统一**：`discover_sources` 签名在 6 个语言中各不相同，后续可统一
- **Python project_dir 估算不准**：`os.path.dirname(file_path)` 不一定是项目根，应从 matcher 传入 `target_directory`
- **Go/C 全局列表污染**：已在问题 4 E8 记录

---

## 问题 7：多层间接调用

### 7.1 现状

当前 find_sinks 赋值追踪只做 1 层：`var = sink_func → var(args)` 命中。多层链式不支持：

```
a = system       # 第一层
b = a             # 第二层
b(user_input)     # ❌ 追不到
```

### 7.2 修复方向：回到分析入口重新判定

find_sinks **不需要自己做递归赋值链追踪**，而是做一步赋值追踪后，**把调用替换为新变量，重新回到 find_sinks 入口**：

```
find_sinks 发现 b(user_input)
→ 赋值追踪一步：b = a
→ a 不是 sink → 不继续递归
→ 把 b 替换为 a，重新进入 find_sinks 判定 a(user_input)
→ 赋值追踪一步：a = system
→ system 是 sink → 标记间接调用
```

循环终止条件：
- 追到的变量就是 sink 名 → 标记间接调用
- 追到函数调用返回值 → 不是间接调用模式，放弃
- 追不到赋值来源 → 放弃

这样完全复用 find_sinks 已有逻辑，不需要单独写递归链追踪，也不需要改 indirect_map 数据结构和 scan_parser 处理逻辑。
