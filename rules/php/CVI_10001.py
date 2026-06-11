# -*- coding: utf-8 -*-

"""
    auto rule template
    ~~~~
    :author:    LoRexxar <LoRexxar@gmail.com>
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

from utils.api import *

class CVI_10001(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):

        self.svid = 10001
        self.language = "php"
        self.vulnerability = "Reflected XSS"
        self.description = "echo参数可控会导致XSS漏洞"
        self.level = 4

        # status
        self.status = False

        # 部分配置
        self.match_mode = "vustomize-match"
        self.match = r"(echo\s?['\"]?(.+?)?\$(.+?)?['\"]?(.+?)?;)"

    def main(self, regex_string):
        """
        regex string input
        :regex_string: regex match string
        :return:
        """
        sql_sen = regex_string[0][0]
        reg = r"\$\w+"
        if re.search(reg, sql_sen, re.I):
            p = re.compile(reg)
            match = p.findall(sql_sen)
            return match
        return None
