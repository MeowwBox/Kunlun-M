# -*- coding: utf-8 -*-
"""
批量让 CVI 规则继承 SingleRuleMixin，并删除与基类默认值相同的冗余字段赋值。

用法：
    python scripts/fix_rule_inheritance.py
"""

import os
import re
import glob

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RULES_DIR = os.path.join(PROJECT_ROOT, "rules")

# 需要排除的目录
EXCLUDE_DIRS = {"test", "tamper"}

# 与基类默认值相同、应删除的 (field, value_pattern) 对
# 每个元素是 (正则匹配模式, 描述)
REDUNDANT_PATTERNS = [
    # author 为以下三种值时删除
    (r'^\s*self\.author\s*=\s*["\']Kunlun-M["\']\s*$', "author=Kunlun-M"),
    (r'^\s*self\.author\s*=\s*["\']KunLun-M["\']\s*$', "author=KunLun-M"),
    (r'^\s*self\.author\s*=\s*["\']LoRexxar["\']\s*$', "author=LoRexxar"),
    # 以下字段赋值为 None / True / [] 时删除
    (r'^\s*self\.black_list\s*=\s*None\s*$', "black_list=None"),
    (r'^\s*self\.keyword\s*=\s*None\s*$', "keyword=None"),
    (r'^\s*self\.unmatch\s*=\s*None\s*$', "unmatch=None"),
    (r'^\s*self\.match_name\s*=\s*None\s*$', "match_name=None"),
    (r'^\s*self\.vul_function\s*=\s*None\s*$', "vul_function=None"),
    (r'^\s*self\.extra_repair_functions\s*=\s*\[\]\s*$', "extra_repair_functions=[]"),
    (r'^\s*self\.framework_deps\s*=\s*\[\]\s*$', "framework_deps=[]"),
    (r'^\s*self\.config_patterns\s*=\s*None\s*$', "config_patterns=None"),
    (r'^\s*self\.exclude_patterns\s*=\s*None\s*$', "exclude_patterns=None"),
    (r'^\s*self\.status\s*=\s*True\s*$', "status=True"),
]

# 编译所有冗余模式
REDUNDANT_COMPILED = [re.compile(p) for p, _ in REDUNDANT_PATTERNS]

# class 定义行替换
CLASS_DEF_RE = re.compile(r'^class (CVI_\d+)\(\):')

# 段落注释（可能因下方字段全部删除而成为孤立注释）
SECTION_COMMENTS = [
    "# status",
    "# 部分配置",
    "# for solidity",
    "# for chrome ext",
    "# for regex",
]

# 用于删除空行的模式：连续两个以上空行 → 两个空行
MULTI_BLANK_RE = re.compile(r'\n{3,}')


def is_redundant_line(line):
    """判断一行是否是与基类默认值相同的冗余赋值"""
    for pat in REDUNDANT_COMPILED:
        if pat.match(line):
            return True
    return False


def is_section_comment(line):
    """判断一行是否是段落注释"""
    stripped = line.strip()
    return stripped in SECTION_COMMENTS


def is_orphaned_comment(lines, idx):
    """
    判断 lines[idx] 处的段落注释是否已孤立：
    1. 紧跟一个空行（说明其下面的字段赋值已被删除）
    2. 下一个非空行是另一个段落注释、def/class、或超出范围
    """
    # 条件1: 紧跟空行（注释与字段之间原本没有空行，现在有了说明字段被删）
    if idx + 1 < len(lines) and lines[idx + 1].strip() == "":
        return True
    # 条件2: 后面全是空行直到另一个段落注释或 def/class
    j = idx + 1
    while j < len(lines) and lines[j].strip() == "":
        j += 1
    if j >= len(lines):
        return True
    next_stripped = lines[j].strip()
    if next_stripped.startswith("def ") or next_stripped.startswith("class "):
        return True
    if is_section_comment(lines[j]):
        return True
    return False


def process_file(filepath):
    """处理单个 CVI 文件，返回 (modified, stats)"""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original_lines = content.split("\n")
    lines = list(original_lines)
    stats = {"removed_lines": 0, "class_changed": False}

    # Step 1: 替换 class 定义
    new_lines = []
    for line in lines:
        m = CLASS_DEF_RE.match(line)
        if m:
            new_line = f"class {m.group(1)}(SingleRuleMixin):"
            if new_line != line:
                stats["class_changed"] = True
            new_lines.append(new_line)
        else:
            new_lines.append(line)
    lines = new_lines

    # Step 2: 删除冗余字段赋值行
    new_lines = []
    for line in lines:
        if is_redundant_line(line):
            stats["removed_lines"] += 1
            continue
        new_lines.append(line)
    lines = new_lines

    # Step 2b: 删除孤立的段落注释
    new_lines = []
    for i, line in enumerate(lines):
        if is_section_comment(line) and is_orphaned_comment(lines, i):
            stats["removed_lines"] += 1
            continue
        new_lines.append(line)
    lines = new_lines

    # Step 2c: 合并连续多余空行（3+个换行 → 2个换行）
    result = "\n".join(lines)
    result = MULTI_BLANK_RE.sub("\n\n", result)

    if result != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(result)
        return True, stats

    return False, stats


def main():
    # 收集所有 CVI_*.py 文件（排除 test/ 和 tamper/）
    cvi_files = []
    for dirpath, dirnames, filenames in os.walk(RULES_DIR):
        # 计算相对于 rules/ 的路径部分
        rel_dir = os.path.relpath(dirpath, RULES_DIR)
        first_part = rel_dir.split(os.sep)[0] if rel_dir != "." else ""
        if first_part in EXCLUDE_DIRS:
            dirnames.clear()  # 不递归进排除目录
            continue
        for fname in filenames:
            if fname.startswith("CVI_") and fname.endswith(".py"):
                cvi_files.append(os.path.join(dirpath, fname))

    cvi_files.sort()

    total_modified = 0
    total_removed = 0
    total_class_changed = 0

    for filepath in cvi_files:
        modified, stats = process_file(filepath)
        if modified:
            rel = os.path.relpath(filepath, PROJECT_ROOT)
            print(f"  [MOD] {rel}  (-{stats['removed_lines']} lines"
                  f"{', class updated' if stats['class_changed'] else ''})")
            total_modified += 1
            total_removed += stats["removed_lines"]
            if stats["class_changed"]:
                total_class_changed += 1

    print(f"\n{'='*60}")
    print(f"修改文件数: {total_modified}/{len(cvi_files)}")
    print(f"类定义更新: {total_class_changed}")
    print(f"删除冗余行: {total_removed}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
