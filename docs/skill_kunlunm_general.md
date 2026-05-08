# Kunlun-M Skill（kunlun-m-general）

这个文档面向“落地执行”：所有操作优先通过 skill 自带脚本完成（下载/初始化/扫描/生成/回归/可选同步）。

## 触发场景（你在做什么时会用到它）

Kunlun-M 是静态白盒漏洞扫描工具，可用于扫描 PHP / JavaScript / Solidity / Chrome Extension 等源代码。满足任一条件就可以触发使用本 skill：

- 你要运行 `python kunlun.py scan ...` 对源码目录做扫描
- 你要运行 `python kunlun.py generate rule ...` 定义/调整 sink（危险点）
- 你要运行 `python kunlun.py generate tamper ...` 定义/调整 source（输入源）与 repair（净化函数）

## 1) 一键准备环境（没项目也能跑）

在任意工作目录执行：

```bash
python skills/kunlun-m-general/scripts/bootstrap_kunlunm.py --repo-dir ./Kunlun-M
```

默认行为：优先 git clone，失败回退 zip；然后自动执行依赖安装、复制 `settings.py`、初始化 DB、load rules/tamper。输出为 Kunlun-M 项目目录路径。

## 2) 日常操作统一用 kunlun_ops.py

约定：`--repo-root` 指向 Kunlun-M 目录（里面有 `kunlun.py`）。

### 扫描

```bash
python skills/kunlun-m-general/scripts/kunlun_ops.py --repo-root ./Kunlun-M scan -t <target> -lan php -b vendor,node_modules -d
```

### 自定义 source/sink 扫描时如何落地（核心）

- sink（危险点）→ 生成/调整 rule，然后 `scan -r <id>` 回归
- source（输入源）+ repair（净化函数）→ 生成/调整 tamper，然后 `scan -tp <name>` 回归

### 生成 rule（定义 sink）

```bash
python skills/kunlun-m-general/scripts/kunlun_ops.py --repo-root ./Kunlun-M gen-rule -lan php --name "<rule_name>" --match "<sink_regex>"
python skills/kunlun-m-general/scripts/kunlun_ops.py --repo-root ./Kunlun-M scan -t <target> -lan php -r <id>
```

### 生成 tamper（定义 source/repair）

```bash
python skills/kunlun-m-general/scripts/kunlun_ops.py --repo-root ./Kunlun-M gen-tamper --name <proj> --controlled "<sources>"
python skills/kunlun-m-general/scripts/kunlun_ops.py --repo-root ./Kunlun-M scan -t <target> -lan php -tp <proj>
```

### 同步到数据库（可选）

只在需要 Web 端管理时做同步：

```bash
python skills/kunlun-m-general/scripts/kunlun_ops.py --repo-root ./Kunlun-M sync --rule --tamper
```

## 3) 平台结构适配

不同平台通常只要求 skill 放置在特定目录，可参考：

- `skills/kunlun-m-general/platforms/README.md`
- 一键复制：`python skills/kunlun-m-general/scripts/install_platform.py --platform <openclaw|codex|claude-code|hermes> --scope <user|project> --repo-root <repo> --force`

## 4) 相关文档

- CLI： [cli.md](./cli.md)
- Rule： [rules.md](./rules.md)
- Tamper： [tamper.md](./tamper.md)

## 测试命令（冒烟验证）

```bash
python skills/kunlun-m-general/scripts/bootstrap_kunlunm.py --repo-dir ./Kunlun-M --force
python skills/kunlun-m-general/scripts/kunlun_ops.py --repo-root ./Kunlun-M gen-rule -lan php --name "Skill Smoke Rule" --match "echo|print" --force
python skills/kunlun-m-general/scripts/kunlun_ops.py --repo-root ./Kunlun-M gen-tamper --name skill_smoke --controlled "$_GET,$_POST" --force
python skills/kunlun-m-general/scripts/kunlun_ops.py --repo-root ./Kunlun-M scan -t ./Kunlun-M/tests -lan php -d
```

## 报告（给 skill/CI 使用的稳定输出）

Kunlun-M 自带 CI 报告脚本 [ci_scan.py](file:///d:/program/Kunlun_M/tools/ci_scan.py)，默认输出 JSON 报告（`meta/summary/vulnerabilities/exit`），适合 skill 消费。

```bash
python tools/ci_scan.py --target ./Kunlun-M/tests --output artifacts/kunlun-ci.json --fail-on none
python skills/kunlun-m-general/scripts/render_ci_report.py --input artifacts/kunlun-ci.json --output artifacts/kunlun-ci.md
```
