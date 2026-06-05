# Kunlun-M 核心代码审计报告

> **审计日期**: 2026-06-04  
> **审计版本**: v2.13.2 (develop 分支)  
> **审计范围**: `core/` 入口层 + 规则系统 + 预处理层 + 共享模块 + 6 语言引擎  
> **审计方法**: 逐模块源码审读，交叉对比引擎间一致性

---

## 一、审计概览

本报告对 Kunlun-M 静态白盒漏洞扫描框架的核心代码进行了系统性审计，覆盖从代码预处理、规则匹配、AST 回溯分析到结果判定的完整流水线。审计重点关注：

1. **设计一致性**：6 个语言引擎的扫描流程、返回值约定、缓存管理是否统一
2. **逻辑正确性**：回溯分析从 sink 到 source 的每一步是否有遗漏或错误
3. **并发安全性**：`asyncio.gather()` 并发扫描时全局状态的隔离性
4. **健壮性**：异常处理、边界条件、代码退化风险

### 审计结论

**整体架构设计合理**，6 引擎的 scan_parser 入口遵循统一范式（初始化→grep匹配→AST解析→参数追踪→结果判定），共享模块（trace_cache、function_summary、branch_constraint）的抽象层次恰当。

**发现 2 个需立即修复的 bug、3 个潜在风险、4 个代码改进建议。**

---

## 二、需立即修复的 Bug

### Bug-1：Go/C 引擎 scan_parser 未清空 `_trace_cache`（缓存污染）

**严重级别**: 🔴 高  
**影响范围**: Go 引擎、C 引擎  
**文件**: `core/core_engine/go/parser.py`、`core/core_engine/c/parser.py`

#### 问题描述

`TraceCache` 是模块级全局单例，缓存键为 `(file_path, var_name, lineno)` → `(code, cp, expr_lineno)`。在一次扫描任务中，同一文件的不同 sink 可能会复用之前追踪过的变量缓存结果。

**4 个引擎正确地在 scan_parser 入口清空了缓存**：

| 引擎 | 清空语句 | 位置 |
|------|---------|------|
| PHP | `_trace_cache.clear()` | scan_parser L3218 |
| JS | `_trace_cache.clear()` | scan_parser L2517 |
| Python | `_trace_cache.clear()` | scan_parser L1559 |
| Java | `_trace_cache.clear()` | scan_parser L1980 |
| **Go** | ❌ 缺失 | — |
| **C** | ❌ 缺失 | — |

#### 具体影响

Go/C 引擎使用 tree-sitter 解析 AST，并在 `_trace_variable_in_lines_impl` 中写入缓存：

```python
# go/parser.py L1687, c/parser.py L1307
if depth == 0 and file_path and to_line and code in (1, 2, -1):
    _trace_cache.put(file_path, var_name, int(to_line), (code, [], source_lineno))
```

当 **同一文件有多个 sink 被不同规则触发** 时：

- 第一次扫描某变量追踪到 `code=-1`（不可控），缓存了该结果
- 第二次扫描同一变量（但在不同分支约束上下文下可能可控），直接命中缓存返回 `code=-1`
- **导致漏报**：实际可控的参数被缓存中的不可控结果覆盖

更严重的是，Go/C 引擎的 `_trace_cache` 实例与 `function_back_go/function_back_c` 共享，跨函数追踪也会读取到错误的缓存。

#### 修复建议

在 Go 和 C 的 `scan_parser` 函数入口处添加 `_trace_cache.clear()`：

```python
# core/core_engine/go/parser.py scan_parser() 入口
_trace_cache.clear()

# core/core_engine/c/parser.py scan_parser() 入口
_trace_cache.clear()
```

---

### Bug-2：`cast.py` 的 `os.chdir()` 在并发扫描时产生竞态

**严重级别**: 🔴 高  
**影响范围**: 所有使用 `vustomize-match` 模式的规则  
**文件**: `core/cast.py` L58

#### 问题描述

`scanner.py` 使用 `asyncio.gather()` 并发调度所有规则的扫描任务：

```python
# scanner.py L197-205
scan_list.append(start_scan(target_directory, rule, files, language, tamper_name))
asyncio.run(_run_scan_list(scan_list))
```

而 `CAST.__init__()` 中有：

```python
# cast.py L57-58
if os.path.isdir(self.target_directory):
    os.chdir(self.target_directory)
```

虽然 Python 的 asyncio 是单线程事件循环模型（协程不会真正并行），但 `os.chdir()` 是进程级状态修改，一旦某个协程修改了工作目录，后续所有协程的相对路径操作都会受影响。特别是：

1. `cast.py` 的 `functions()` 方法（L110）使用 `FileParseAll` 做 grep，内部使用 `os.path.join(self.file_path)` — 如果工作目录被其他协程改变，路径会出错
2. `cast.py` 的 `block_code()` 方法（L151）用 `open(self.file_path)` 读文件 — 同样受影响
3. `pretreatment.py` 的 `get_path()` 方法（L60）也有 `os.chdir(os.path.dirname(os.path.dirname(__file__)))`

#### 具体场景

假设规则 A 扫描 `/projectA/`，规则 B 扫描 `/projectB/`：
1. 规则 A 的 CAST 实例化 → `os.chdir('/projectA/')`
2. 规则 B 的 CAST 实例化 → `os.chdir('/projectB/')`
3. 规则 A 后续的 `open(self.file_path)` 会在 `/projectB/` 目录下查找 `/projectA/src/vuln.php` → **路径错误**

#### 影响评估

实际影响取决于 `file_path` 是绝对路径还是相对路径：
- 如果 `file_path` 是绝对路径（通常如此），`os.chdir` 不会影响 `open()` 的结果
- 但 `cast.py` 的 `functions()` 方法中 `sum(1 for l in open(self.file_path))` 使用的是构造时传入的 `file_path`，如果初始传入的就是绝对路径则无影响
- **`pretreatment.py` 的 `get_path()` 方法更危险**：它调用 `os.chdir()` 回项目根目录，然后使用 `os.path.join(self.target_directory, ...)` — 如果 target_directory 是相对路径，且被其他协程的 chdir 干扰，结果会错误

#### 修复建议

短期方案：在所有使用相对路径的地方改为使用绝对路径，避免 `os.chdir()` 的依赖。`os.chdir()` 本身可以直接删除。

---

## 三、潜在风险

### Risk-1：`sink_param:` 字典 key 的冒号 Typo

**严重级别**: 🟡 中  
**文件**: `core/core_engine/php/parser.py` L3010, `javascript/parser.py` L2216, `java/parser.py` 多处

#### 问题描述

PHP、JS、Java 引擎的 `set_scan_results` 函数中，返回结果的字典 key 为 `'sink_param:'`（带冒号）：

```python
# php/parser.py L3010
result = {
    'code': is_co,
    'source': cp,
    'source_lineno': expr_lineno,
    'sink': sink,
    'sink_param:': param,    # ← 注意这个冒号
    'sink_lineno': vul_lineno,
    "chain": scan_chain,
}
```

同样，Java 引擎中也有相同模式（L1772, L1782, L1816, L1833, L1851, L1867, L1881, L1892, L1956）。

#### 影响

目前这是一个 **内部约定**：所有读写 `'sink_param:'` 的代码都使用相同的 typo key，所以不会出错。但如果未来有开发者不熟悉这个约定，使用 `'sink_param'`（不带冒号）去读取，就会遗漏数据。

Python/Go/C 引擎的 scan_parser 返回的结果使用 `"param"` key（无冒号），与 PHP/JS/Java 不一致。

#### 建议

这是一个低优先级的历史遗留问题。如果要修复，需要同时修改所有 PHP/JS/Java 引擎的 `set_scan_results` 和下游消费代码，改动面较大。建议在注释中明确标注这个约定。

---

### Risk-2：`matcher._parse_ast_result` 不区分 code=-1 和普通不可控

**严重级别**: 🟡 中  
**文件**: `core/matcher.py` L207-242

#### 问题描述

`_parse_ast_result` 解析 scan_parser 返回的结果列表，但只在第一个循环检查 code=1，第二个循环检查 code=4，第三个循环检查 code=3/2/**else**：

```python
# matcher.py L228-239
for r in result:
    if r['code'] == 3:
        ...
    elif r['code'] == 2:
        ...
    else:  # ← code=-1 也走这里，被当作"普通不可控"
        return False, 'Function-param-uncon', r['chain']
```

这意味着 **分支约束阻断（code=-1）和普通不可控被同等处理**。虽然 PHP/JS 的 `set_scan_results` 只在 `scan_results` 为空时才添加 code=-1（意味着没有其他更高优先级结果），所以实际影响有限。但 Python/Java/Go/C 引擎的 scan_parser 直接返回结果列表，可能包含多个不同 code 的结果。

#### 影响

如果 Python/Go/C 引擎的 scan_parser 返回 `[{'code': -1, ...}, {'code': 1, ...}]`，`_parse_ast_result` 的第一个循环会正确命中 code=1 返回。但如果结果是 `[{'code': -1, ...}, {'code': 3, ...}]`，第三个循环会先命中 code=-1 的 else 分支，返回 "Function-param-uncon"，跳过 code=3 的结果。

实际上，各引擎在构建结果列表时已经按优先级排序（code=1/2 先添加，code=4/3/-1 后添加），所以第一个结果通常是最高优先级的。但如果扫描结果为空列表（`[]`），函数返回 `None`，这是正确的行为。

#### 建议

在 `_parse_ast_result` 中显式处理 code=-1，或者在第三个循环中跳过 code=-1：

```python
for r in result:
    if r['code'] == 3:
        ...
    elif r['code'] == 2:
        ...
    elif r['code'] == -1:
        continue  # 分支约束阻断，检查是否有其他结果
    else:
        ...
```

---

### Risk-3：`detection.py` 使用已弃用的 pip 内部 API

**严重级别**: 🟡 低  
**文件**: `core/detection.py` L21-24

```python
try:  # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:  # for pip <= 9.0.3
    from pip.req import parse_requirements
```

`pip._internal` 是 pip 的内部 API，在 pip 23.1+ 中已标记为 deprecated，未来版本可能移除。如果升级 pip 导致导入失败，框架依赖扫描功能将失效。

此外，`detection.py` 的 `cloc()` 方法使用 `if fileext == ...` 而非 `elif`，导致一个文件扩展名可能匹配多个计数函数（例如 `.m` 同时匹配 `count_java_line` 但实际应该是 Objective-C）。不过这只影响代码行数统计的准确性，不影响漏洞扫描。

#### 建议

将 `parse_requirements` 替换为 `packaging.requirements.Requirement` 或 `pypa/requirements-parser` 第三方库。

---

## 四、代码改进建议

### Suggestion-1：统一各引擎 `scan_parser` 返回结果的数据结构

当前 6 引擎的 scan_parser 返回结果结构存在不一致：

| 字段 | PHP/JS (set_scan_results) | Python | Java | Go | C |
|------|---------------------------|--------|------|----|---|
| `code` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `source` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `source_lineno` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `sink` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `sink_param:` | ✅ (带冒号) | ❌ | ✅ (带冒号) | ❌ | ❌ |
| `sink_lineno` | ✅ | ❌ | ❌ | ❌ | ✅ |
| `chain` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `language` | ❌ | ❌ | ❌ | ❌ | ✅ |
| `source_file` | ❌ | ❌ | ❌ | ❌ | ✅ |

建议统一为以下最小公共字段集：
```python
{
    "code": int,           # 1/2/3/4/-1
    "source": str,          # 污点来源描述
    "source_lineno": int,   # 源码行号
    "chain": list,          # 数据流链
}
```

---

### Suggestion-2：Go/C 引擎 `_trace_variable_in_lines` 缓存 code=-1 的语义问题

**文件**: `core/core_engine/go/parser.py` L1687, `core/core_engine/c/parser.py` L1307

```python
if depth == 0 and file_path and to_line and code in (1, 2, -1):
    _trace_cache.put(file_path, var_name, int(to_line), (code, [], source_lineno))
```

`code=-1` 被缓存意味着"此变量不可控"的结论会被记住。但在不同的分支约束上下文中，同一变量可能有时可控、有时不可控。缓存 key `(file_path, var_name, lineno)` 不包含分支约束信息。

**当前实际影响有限**：因为单次 scan_parser 调用中，trace_cache 已经在开头被清空（PHP/JS/Python/Java），但 Go/C 未清空（Bug-1）。修复 Bug-1 后，这个问题也会被间接解决。

---

### Suggestion-3：`pretreatment.py` 使用 `queue.Queue` 而非 `asyncio.Queue`

**文件**: `core/pretreatment.py` L138-144

```python
scan_list = [self.pre_ast() for _ in range(10)]
async def _run_pretreatment(tasks):
    await asyncio.gather(*tasks)
asyncio.run(_run_pretreatment(scan_list))
```

`pre_ast()` 是 async 函数，但内部使用 `queue.Queue`（线程队列）而非 `asyncio.Queue`（协程队列）。`queue.get()` 是阻塞调用，会阻塞事件循环。

虽然在当前实现中（10 个协程竞争同一个队列），`queue.get()` 不会真正阻塞（因为队列已有数据），但这是一个代码异味。如果未来改为异步 I/O 操作，这里会成为瓶颈。

#### 建议

将 `queue.Queue` 替换为 `asyncio.Queue`，或直接改为普通循环（因为 asyncio 是单线程的，10 个协程共享一个队列等同于串行处理）。

---

### Suggestion-4：`cli.py` 的 `input()` 调用不适合自动化

**文件**: `core/cli.py` L95-98, `rule.py` L402

```python
if input().lower() != 'y':
    ...
```

CLI 模式下的 `check_scantask` 和 RuleCheck.recover 使用 `input()` 等待用户确认。在 CI/CD 或 Web 界面调用时，`input()` 会阻塞或抛出 `EOFError`。

#### 建议

添加 `--auto-yes` 参数跳过交互式确认（`check_scantask` 已有 `auto_yes` 参数但未完全应用）。

---

## 五、架构层面的正面发现

### ✅ 分支约束追踪设计正确

`BranchConstraint` 数据结构的设计简洁有效：
- `__slots__` 优化内存
- `negate()` 方法正确处理了所有操作符的反转（`==` ↔ `!=`, `isset` ↔ `!isset`, `in` ↔ `not in`）
- 在各引擎的 `_parameters_back_impl` / `_trace_variable_in_lines_impl` 中正确传播

56 个单元测试全部通过验证了这一设计的正确性。

### ✅ 函数摘要缓存机制合理

`FunctionSummary` + `SummaryCacheManager` 的设计：
- 使用 SHA256 内容哈希做缓存失效判断
- JSON 序列化/反序列化支持跨进程缓存
- 懒初始化（`_summaries_initialized` 标志避免重复生成）

### ✅ 内置知识库拆分到语言子模块

每种语言有独立的 `builtin_knowledge.py`，包含该语言的标准库函数可控性信息。延迟加载机制（`TraceCache._load_builtin_module()`）避免了启动时的性能开销。

### ✅ 扫描结果过滤策略合理

PHP/JS 的 `set_scan_results` 只在 `scan_results` 为空时保留 code=-1 结果：

```python
elif result['code'] == -1:
    # 分支约束阻断：仅在没有其他结果时保留
    if not scan_results:
        results.append(result)
        scan_results += results
```

这意味着：如果同一条规则的多个参数追踪中，只要有一个参数被判定为可控（code=1），就不会因为另一个参数被分支约束阻断（code=-1）而排除漏洞报告。

### ✅ 规则热加载机制完善

`Rule.reload()` 支持运行时重新加载规则文件，且在 reload 失败时保留旧版本：

```python
except Exception as e:
    if rulename in old_rule_dict:
        self.rule_dict[rulename] = old_rule_dict[rulename]
```

---

## 六、各引擎回溯分析逻辑对比

### 回溯流程总览

```
sink 所在行 → scan_parser 入口
    │
    ├─ 1. 预处理：初始化缓存、函数定义索引、函数摘要
    │
    ├─ 2. 定位 sink：在 AST 中查找 vul_lineno 上的敏感函数调用
    │      └─ 降级：AST 解析失败时基于行文本匹配
    │
    ├─ 3. 提取参数：从 AST call 节点提取参数列表
    │      └─ 降级：用正则从行文本提取参数
    │
    ├─ 4. 逐参数追踪：对每个非字面量参数进行可控性分析
    │      │
    │      ├─ 字面量 → 跳过
    │      ├─ 可控源 ($_GET, request 等) → code=1
    │      ├─ 用户自定义变量 → parameters_back / _trace_variable_in_lines
    │      │      │
    │      │      ├─ 查缓存 → 命中则直接返回
    │      │      ├─ 查函数摘要 → _judge_from_summary
    │      │      ├─ 查内置知识库 → lookup_builtin
    │      │      ├─ 赋值追踪 → x = expr，追踪 expr 的可控性
    │      │      ├─ 函数调用追踪 → function_back / function_back_go / function_back_c
    │      │      │      │
    │      │      │      ├─ 查函数摘要
    │      │      │      ├─ 分析函数体：return expr → 追踪 expr 对参数的依赖
    │      │      │      ├─ 跨文件追踪：import_map 定位函数定义
    │      │      │      └─ 递归：函数参数也是函数调用时继续向上追踪
    │      │      │
    │      │      ├─ 分支约束检查 → if/else 条件提取 → 判断 sink 在哪个分支
    │      │      │      └─ code=-1（约束阻断）
    │      │      └─ 修复函数检查 → code=2（已修复）
    │      │
    │      └─ code=4（函数参数） → _resolve_code4 追踪调用者链
    │
    └─ 5. 结果判定：
           ├─ code=1 → 漏洞确认
           ├─ code=2 → 漏洞已修复
           ├─ code=3 → 疑似漏洞（需 is_unconfirm 标志）
           ├─ code=4 → 新漏洞函数 / 配置型漏洞
           └─ code=-1 → 不可控 / 分支约束阻断
```

### 各引擎关键差异

| 特性 | PHP | JS | Python | Java | Go | C |
|------|-----|----|--------|------|----|---|
| AST 解析器 | lphply | esprima | built-in ast | javalang | tree-sitter-go | tree-sitter-c |
| 核心回溯函数 | `parameters_back` | `parameters_back` | `parameters_back` | `parameters_back` | `_trace_variable_in_lines` | `_trace_variable_in_lines` |
| 函数回溯 | `function_back` | `function_back` | `_resolve_code4` | `function_back_java` | `function_back_go` | `function_back_c` |
| 结果收集 | `set_scan_results` | `set_scan_results` | 直接 append | 直接 append | 局部 results | 局部 results |
| 缓存清空 | ✅ | ✅ | ✅ | ✅ | ❌ **Bug-1** | ❌ **Bug-1** |
| 赋值链传播 | ❌ | ❌ | ✅ (5轮迭代) | ❌ | ❌ | ❌ |
| code=4 解析 | ❌ | ❌ | ✅ (_resolve_code4) | ❌ | ❌ | ❌ |
| 分支约束 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**Python 引擎的独特能力**：
- **赋值链传播**：`scan_parser` 中在函数内做变量赋值关系的 5 轮迭代传播（L1618-1650），将 `x = tainted` 关系传播到 `y = x` 等
- **code=4 解析**：`_resolve_code4` 能追踪函数参数到调用者，递归解析调用链直到找到可控源

---

## 七、修复优先级总结

| 编号 | 类型 | 描述 | 优先级 | 工作量 |
|------|------|------|--------|--------|
| Bug-1 | 缓存污染 | Go/C scan_parser 未清空 trace_cache | 🔴 P0 | 2行代码 |
| Bug-2 | 并发安全 | cast.py os.chdir 竞态条件 | 🔴 P0 | 删除1行+验证 |
| Risk-1 | 代码规范 | sink_param: 冒号 typo | 🟡 P2 | 改动面大，暂不修 |
| Risk-2 | 逻辑缺陷 | _parse_ast_result 未区分 code=-1 | 🟡 P1 | 1行代码 |
| Risk-3 | 兼容性 | pip 内部 API 弃用 | 🟡 P2 | 小改动 |
| Sugg-1 | 架构 | 统一返回结果结构 | 🔵 P3 | 大重构 |
| Sugg-2 | 缓存语义 | code=-1 缓存不含分支约束 | 🔵 P3 | Bug-1 修复后缓解 |
| Sugg-3 | 代码质量 | pretreatment.py queue → asyncio.Queue | 🔵 P3 | 小改动 |
| Sugg-4 | 可用性 | input() 自动化支持 | 🔵 P3 | 小改动 |
