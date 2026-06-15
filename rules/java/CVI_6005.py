# -*- coding: utf-8 -*-

"""
    Java Insecure Deserialization Rule (AST-enhanced)
    ~~~~
    :author:    KunLun-M
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

import re

from utils.api import *

class CVI_6005(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):
        self.svid = 6005
        self.language = "java"
        self.vulnerability = "Insecure Deserialization"
        self.description = "通过AST分析检测ObjectInputStream.readObject()、XMLDecoder等反序列化方法的输入源是否来自用户可控数据，追踪数据流以发现反序列化漏洞。建议使用ObjectInputFilter或ValidatingObjectInputStream进行过滤。"
        self.level = 9

        # 部分配置
        self.match_mode = "only-regex"
        self.match = [
            r"(?:new\s+ObjectInputStream|\.readObject\s*\(|new\s+XMLDecoder)",
        ]

        # for regex
        self.unmatch = [
            r"ObjectInputFilter",
            r"ValidatingObjectInputStream",
            r"SafeObjectInputStream",
        ]

    def main(self, regex_string):
        """readObject/ObjectInputStream 已足够精确，不需要额外筛选"""
        if not isinstance(regex_string, str):
            regex_string = str(regex_string)
        # 排除安全过滤类
        if re.search(r'ObjectInputFilter|ValidatingObjectInputStream|SafeObjectInputStream', regex_string):
            return False
        return None

