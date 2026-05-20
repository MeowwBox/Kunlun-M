# -*- coding: utf-8 -*-

"""
    Java SpEL/OGNL Injection Rule (AST-enhanced)
    ~~~~
    :author:    KunLun-M
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

from utils.api import *


class CVI_6012():
    """
    rule class
    """

    def __init__(self):
        self.svid = 6012
        self.language = "java"
        self.author = "KunLun-M"
        self.vulnerability = "SpEL/OGNL Injection"
        self.description = "SpEL表达式解析（parseExpression）或OGNL表达式求值（getValue），如果表达式内容可控，可能导致远程代码执行。建议使用SimpleEvaluationContext限制表达式能力。"
        self.level = 9

        # status
        self.status = True

        # 部分配置
        self.match_mode = "function-param-regex"
        self.match = "parseExpression|getValue"

        # for solidity
        self.match_name = None
        self.black_list = None

        # for chrome ext
        self.keyword = None

        # for regex
        self.unmatch = [r"SimpleEvaluationContext"]

        self.vul_function = ["parseExpression", "getValue"]

    def main(self, regex_string):
        pass
