# -*- coding: utf-8 -*-

"""
    Java Insecure Reflection Rule (AST-enhanced)
    ~~~~
    :author:    KunLun-M
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

from utils.api import *


class CVI_6018():
    """
    rule class
    """

    def __init__(self):
        self.svid = 6018
        self.language = "java"
        self.author = "KunLun-M"
        self.vulnerability = "Insecure Reflection"
        self.description = "Class.forName反射加载类，如果类名可控，可能导致任意类加载和远程代码执行。getDeclaredMethod/getMethod如果方法名可控同样存在风险。"
        self.level = 7

        # status
        self.status = True

        # 部分配置
        self.match_mode = "function-param-regex"
        self.match = "forName|getDeclaredMethod|getMethod"

        # for solidity
        self.match_name = None
        self.black_list = None

        # for chrome ext
        self.keyword = None

        # for regex
        self.unmatch = []

        self.vul_function = ["forName", "getDeclaredMethod", "getMethod"]

    def main(self, regex_string):
        pass
