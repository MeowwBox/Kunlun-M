# -*- coding: utf-8 -*-

"""
    Go 开放重定向规则
    ~~~~
    :author:    KunLun-M
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

import re
from utils.api import *


class CVI_8013(SingleRuleMixin):
    """
    Go 开放重定向规则
    匹配 http.Redirect
    """

    def __init__(self):
        self.svid = 8013
        self.language = "go"
        self.vulnerability = "开放重定向"
        self.description = "使用了HTTP重定向函数（http.Redirect），且重定向URL参数可能由用户输入控制，可能导致开放重定向漏洞。建议对重定向URL进行白名单校验，仅允许本站相对路径或可信域名，避免将用户输入直接作为重定向目标。"
        self.level = 5

        self.match_mode = "function-param-regex"
        self.match = r"http\.Redirect\s*\("

        self.vul_function = ["http.Redirect"]

    def main(self, regex_string):
        """
        二次筛选：检查 http.Redirect 的URL参数（第二个参数）是否为硬编码字符串。
        如果是相对路径常量（如 "/login"、"/index"）返回 False，
        如果是变量或外部URL则返回 True。
        """
        if not isinstance(regex_string, str):
            regex_string = str(regex_string)

        match = re.search(r'http\.Redirect\s*\((.*)\)', regex_string)
        if not match:
            return None

        args = match.group(1).strip()

        # 解析参数列表，http.Redirect(w, r, url, code)
        # 尝试提取第三个参数（URL参数，索引2）
        # 简单分割参数
        parts = []
        depth = 0
        current = ""
        for ch in args:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
            elif ch == ',' and depth == 0:
                parts.append(current.strip())
                current = ""
                continue
            current += ch
        if current.strip():
            parts.append(current.strip())

        # 第三个参数是URL（索引2）
        if len(parts) >= 3:
            url_arg = parts[2].strip()

            # 硬编码字符串字面量（相对路径常量），排除
            url_str_match = re.match(r'^"([^"]*)"$', url_arg)
            if url_str_match:
                return False

        # 确认包含 http.Redirect 调用
        if re.search(r'http\.Redirect\s*\(', regex_string):
            return True

        return None
