# -*- coding: utf-8 -*-

"""
    Java Log4Shell Rule
    ~~~~
    :author:    KunLun-M
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

from utils.api import *

class CVI_6017(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):
        self.svid = 6017
        self.language = "java"
        self.vulnerability = "Log4Shell"
        self.description = "检测到Log4j JNDI注入相关特征（${jndi:前缀或JndiLookup），可能遭受CVE-2021-44228 Log4Shell远程代码执行攻击。"
        self.level = 10

        # 部分配置
        self.match_mode = "only-regex"
        self.match = [
            r'\$\{[^}]*jndi\s*:',
            r'JndiLookup',
        ]

        # for regex
        self.unmatch = [r"log4j2\.formatMsgNoLookups", r"NO_LOOKUPS", r"JndiManager"]

    def main(self, regex_string):
        pass
