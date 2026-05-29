# -*- coding: utf-8 -*-

"""
    Go SQL 注入规则
    ~~~~
    :author:    KunLun-M
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

import re
from utils.api import *


class CVI_8002():
    """
    Go SQL 注入规则
    匹配 db.Query/db.Exec/db.QueryRow/db.Prepare/tx.Exec/gorm.DB.Raw/gorm.DB.Where 等
    """

    def __init__(self):
        self.svid = 8002
        self.language = "go"
        self.author = "KunLun-M"
        self.vulnerability = "SQL注入"
        self.description = "使用了可能存在SQL注入风险的数据库操作函数（db.Query、db.Exec、db.QueryRow、gorm.DB.Raw、gorm.DB.Where等），建议使用参数化查询（占位符?）替代字符串拼接。"
        self.level = 8

        # status
        self.status = True

        # 部分配置
        self.match_mode = "function-param-regex"
        self.match = r"\.Query\s*\(|\.Exec\s*\(|\.QueryRow\s*\(|\.Prepare\s*\(|\.Raw\s*\(|\.Where\s*\(|\.Select\s*\(|\.Having\s*\("

        # for solidity
        self.match_name = None
        self.black_list = None

        # for chrome ext
        self.keyword = None

        # for regex
        self.unmatch = [
            r"sql\.Named\(",
            r"\?\s*[,\"]",
            r"\$\d+",
        ]

        self.vul_function = [
            "db.Query", "db.Exec", "db.QueryRow", "db.Prepare",
            "tx.Exec", "tx.Query", "tx.QueryRow", "tx.Prepare",
            "gorm.DB.Raw", "gorm.DB.Where", "gorm.DB.Select", "gorm.DB.Having",
        ]

    def main(self, regex_string):
        """
        二次筛选：检查是否使用参数化查询（占位符?），排除安全写法。
        检测字符串拼接 SQL 的模式（fmt.Sprintf 拼接、+ 连接等）。
        """
        if not isinstance(regex_string, str):
            regex_string = str(regex_string)

        # 安全写法：使用 ? 占位符的参数化查询
        # db.Query("SELECT * FROM users WHERE id = ?", userId)
        if re.search(r'\.\w+\s*\(\s*"[^"]*\?[^"]*"', regex_string):
            return False

        # 安全写法：使用 $N 占位符（PostgreSQL 风格）
        if re.search(r'\.\w+\s*\(\s*"[^"]*\$\d+[^"]*"', regex_string):
            return False

        # 安全写法：使用 sql.Named
        if re.search(r'sql\.Named\s*\(', regex_string):
            return False

        # 危险模式：fmt.Sprintf 拼接 SQL
        if re.search(r'fmt\.Sprintf\s*\(', regex_string):
            return True

        # 危险模式：字符串连接拼接 SQL
        if re.search(r'"[^"]*SELECT\s|"[^"]*INSERT\s|"[^"]*UPDATE\s|"[^"]*DELETE\s|"[^"]*DROP\s', regex_string, re.I):
            if re.search(r'\+\s*\w+', regex_string):
                return True

        # 危险模式：直接将变量传入 SQL 函数（非字符串字面量参数）
        dangerous_patterns = [
            r"\.Query\s*\(\s*\w+",
            r"\.Exec\s*\(\s*\w+",
            r"\.QueryRow\s*\(\s*\w+",
            r"\.Raw\s*\(\s*\w+",
            r"\.Where\s*\(\s*\w+",
        ]
        for pat in dangerous_patterns:
            if re.search(pat, regex_string):
                return True

        return None
