# -*- coding: utf-8 -*-

"""
    Go SQL注入(raw query)规则
    ~~~~
    :author:    KunLun-M
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

import re
from utils.api import *


class CVI_8009(SingleRuleMixin):
    """
    Go SQL注入(raw query)规则
    匹配 db.Query / db.Exec / db.Raw 等
    """

    def __init__(self):
        self.svid = 8009
        self.language = "go"
        self.vulnerability = "SQL注入"
        self.description = "使用了直接拼接SQL语句的数据库查询函数（db.Query、db.Exec、db.Raw等），可能导致SQL注入漏洞。建议使用参数化查询（占位符?）或ORM框架，避免将用户输入直接拼接到SQL语句中。"
        self.level = 8

        self.match_mode = "function-param-regex"
        self.match = r"db\.Query\s*\(|db\.Exec\s*\(|db\.Raw\s*\("

        self.vul_function = ["db.Query", "db.Exec", "db.Raw"]

    def main(self, regex_string):
        """
        二次筛选：检查匹配到的代码行是否为危险的SQL查询调用，
        排除参数是硬编码字符串字面量的情况。
        """
        if not isinstance(regex_string, str):
            regex_string = str(regex_string)

        match = re.search(r'(?:db\.Query|db\.Exec|db\.Raw)\s*\((.*)\)', regex_string)
        if not match:
            return None

        args = match.group(1).strip()

        # 纯字符串字面量参数（硬编码SQL），排除
        # db.Query("SELECT * FROM users WHERE id = ?", 1) 中的SQL模板不算硬编码
        # 仅当整个参数是单个硬编码字符串时排除，如 db.Exec("CREATE TABLE ...")
        if re.match(r'^"[^"]*"$', args):
            return False

        # 确认包含危险的SQL查询调用
        dangerous_patterns = [
            r"db\.Query\s*\(",
            r"db\.Exec\s*\(",
            r"db\.Raw\s*\(",
        ]
        for pat in dangerous_patterns:
            if re.search(pat, regex_string):
                return True

        return None
