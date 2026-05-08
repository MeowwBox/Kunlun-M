# CI/CD 扫描任务驱动（CI Scan Driver）

## 目的

用于在 CI/CD 中以“独立入口”驱动 KunLun-M 扫描，并生成稳定的 JSON 报告文件，同时按阈值返回明确的退出码以实现门禁。

该入口不会改变现有 `python kunlun.py scan ...` 的默认行为。

## 前置条件

- 仓库内必须存在至少一条规则文件：`rules/**/CVI_*.py`
- 若只有 `rules/*.template` 而没有任何 `CVI_*.py`，CI 驱动会直接失败并写出 error JSON（避免“看似通过但实际没有跑规则”的假阴性）
- 规则与 tamper 的机制与目录结构见 [rules.md](./rules.md) 与 [tamper.md](./tamper.md)

## 快速开始

安装依赖：

```bash
python -m pip install -r requirements.txt
```

建议 Python 版本：3.11+（以 requirements.txt 与 GitHub Actions 示例为准）。

运行扫描（生成报告文件，按阈值失败）：

```bash
python tools/ci_scan.py --target . --output artifacts/kunlun-ci.json --fail-on high
```

## 参数

- `--target`：扫描目标路径（默认 `.`）
- `--output`：报告输出路径（默认 `artifacts/kunlun-ci.json`）
- `--fail-on`：失败阈值：`none|low|medium|high|critical`（默认读取环境变量 `KUNLUN_FAIL_ON`，否则 `none`）
- `--include-unconfirm`：是否包含未确认漏洞（默认读取 `KUNLUN_INCLUDE_UNCONFIRM`）
- `--with-vendor` / `--without-vendor`：是否启用 SCA（依赖漏洞）扫描（默认读取 `KUNLUN_WITH_VENDOR`，默认关闭）
- `--rule`：指定规则 ID（逗号分隔），例如 `1000,1001`
- `--language`：指定语言（逗号分隔）
- `--blackpath`：黑名单路径（逗号分隔）
- `--tamper`：拓展插件（tamper）名称
- `--unprecom`：关闭预编译（更快但能力下降）
- `--settings-module`：CI 专用 settings（默认 `Kunlun_M.settings_ci`）

## 环境变量

- `KUNLUN_FAIL_ON`：同 `--fail-on`
- `KUNLUN_INCLUDE_UNCONFIRM`：`0/1`
- `KUNLUN_WITH_VENDOR`：`0/1`

## 退出码

- `0`：扫描成功，且未触发阈值
- `1`：扫描过程异常/初始化失败（同时会写出包含 error 的 JSON）
- `2`：扫描成功，但触发阈值（用于 CI 门禁）

## 门禁逻辑

- 当 `--fail-on none` 时：不触发门禁（只要扫描流程不异常，退出码为 `0`）
- 当 `--fail-on` 为 `low|medium|high|critical` 时：若存在漏洞且最大严重性 `>= fail-on`，退出码为 `2`
- 扫描异常（例如 target 不存在）：退出码为 `1`，并输出包含 `error` 堆栈的 JSON 报告

## 报告格式（JSON）

输出文件为稳定 JSON，结构如下：

- `meta`
  - `target`：扫描目标
  - `task_id` / `project_id`：内部任务与项目 ID（CI settings 下使用隔离的 SQLite）
  - `started_at` / `finished_at`
  - `fail_on` / `include_unconfirm` / `with_vendor` / `settings_module`
- `summary`
  - `total`：漏洞条数
  - `by_severity`：按 `critical/high/medium/low` 统计
  - `max_severity`：`none|low|medium|high|critical`
- `vulnerabilities[]`
  - `cvi_id` / `rule_name` / `severity` / `language`
  - `file`：命中位置（通常为 `path:line`）
  - `result_type` / `source_code` / `is_unconfirm`
- `exit`
  - `code`：`0|1|2`
  - `reason`：`ok|threshold_reached|exception`

## 常见问题

- 运行后直接失败，JSON 里提示 `no rules found under rules/**/CVI_*.py`？
  - 说明当前工作区没有任何规则文件（只有模板或规则未被分发）。需要补齐 `rules/<language>/CVI_<id>.py` 后再跑扫描。
- 扫描目标不存在但 CI 没有失败？
  - 使用 `tools/ci_scan.py` 会在 target 不存在时返回 `1` 并写出 error JSON；请确保 CI job 的执行命令是 `python tools/ci_scan.py ...` 而不是只调用 `kunlun.py scan ...`
- 需要提前执行 `python kunlun.py config load` 吗？
  - 不需要。CI 驱动会直接从 `rules/**/CVI_*.py` 加载规则元信息用于报告展示，并使用 `settings_ci.py` 的 SQLite 自动迁移初始化
- 扫描后仓库里出现了新的空目录（例如 `rules/text/`）？
  - 如果目标目录里包含大量非代码文件（txt、md 等），语言识别可能会带出对应“语言目录名”，而引擎会尝试为缺失的规则语言目录创建占位目录。CI 中建议显式指定扫描语言（例如 `--language php,javascript`），并配合 `--blackpath vendor,node_modules` 降低噪声与副作用。

## CI 配置示例

- GitHub Actions：见 [kunlun-scan.yml](../ci/github-actions/kunlun-scan.yml)（仓库内实际运行位置仍需放在 `.github/workflows/`）
- GitLab CI：见 [kunlun-ci.yml](../ci/gitlab/kunlun-ci.yml)（根目录 `.gitlab-ci.yml` 已通过 include 引用）
- Jenkins：见 [Jenkinsfile](../ci/jenkins/Jenkinsfile)（可在 Jenkins Job 中配置 Script Path 指向该文件）
 
