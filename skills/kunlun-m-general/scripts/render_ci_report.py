# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys
from typing import Any, Dict, List


def _severity_rank(name: str) -> int:
    order = {
        "none": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    return order.get((name or "").lower().strip(), 0)


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _md_escape(s: Any) -> str:
    t = "" if s is None else str(s)
    return t.replace("|", "\\|").replace("\n", "\\n").replace("\r", "")


def render(report: Dict[str, Any], max_items: int) -> str:
    meta = report.get("meta") or {}
    summary = report.get("summary") or {}
    vulns: List[Dict[str, Any]] = list(report.get("vulnerabilities") or [])
    exit_info = report.get("exit") or {}

    vulns.sort(key=lambda x: (-_severity_rank(str(x.get("severity"))), str(x.get("rule_name") or ""), str(x.get("file") or "")))
    shown = vulns[: max(0, int(max_items))]

    lines: List[str] = []
    lines.append("# Kunlun-M 扫描报告")
    lines.append("")
    lines.append("## 元信息")
    lines.append("")
    lines.append("- target: {}".format(_md_escape(meta.get("target"))))
    lines.append("- task_id: {}".format(_md_escape(meta.get("task_id"))))
    lines.append("- project_id: {}".format(_md_escape(meta.get("project_id"))))
    lines.append("- started_at: {}".format(_md_escape(meta.get("started_at"))))
    lines.append("- finished_at: {}".format(_md_escape(meta.get("finished_at"))))
    lines.append("- settings_module: {}".format(_md_escape(meta.get("settings_module"))))
    lines.append("")
    lines.append("## 汇总")
    lines.append("")
    lines.append("- total: {}".format(_md_escape(summary.get("total"))))
    lines.append("- max_severity: {}".format(_md_escape(summary.get("max_severity"))))
    lines.append("- by_severity: {}".format(_md_escape(summary.get("by_severity"))))
    lines.append("")
    lines.append("## 发现项（Top {}）".format(len(shown)))
    lines.append("")
    lines.append("| severity | cvi_id | rule_name | language | file | is_unconfirm |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for v in shown:
        lines.append(
            "| {} | {} | {} | {} | {} | {} |".format(
                _md_escape(v.get("severity")),
                _md_escape(v.get("cvi_id")),
                _md_escape(v.get("rule_name")),
                _md_escape(v.get("language")),
                _md_escape(v.get("file")),
                _md_escape(v.get("is_unconfirm")),
            )
        )

    if len(vulns) > len(shown):
        lines.append("")
        lines.append("已截断：共 {} 条，仅展示前 {} 条。".format(len(vulns), len(shown)))

    lines.append("")
    lines.append("## 退出码")
    lines.append("")
    lines.append("- code: {}".format(_md_escape(exit_info.get("code"))))
    lines.append("- reason: {}".format(_md_escape(exit_info.get("reason"))))
    lines.append("")
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    p = argparse.ArgumentParser(prog="render_ci_report")
    p.add_argument("--input", dest="input", default="artifacts/kunlun-ci.json")
    p.add_argument("--output", dest="output", default="-")
    p.add_argument("--max-items", dest="max_items", type=int, default=200)
    args = p.parse_args(argv)

    report = _read_json(os.path.abspath(args.input))
    out = render(report, args.max_items)
    if args.output == "-" or not args.output:
        sys.stdout.write(out)
        return 0

    out_path = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

