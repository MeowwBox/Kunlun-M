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

class CVI_1003(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):

        self.svid = 1003
        self.language = "php"
        self.author = "LoRexxar/wufeifei"
        self.vulnerability = "SSRF"
        self.description = "get_headers的参数可控，可能会导致SSRF漏洞"
        self.level = 7

        # status
        self.status = False

        # 部分配置
        self.match_mode = "function-param-regex"
        self.match = r"get_headers"

    def main(self, regex_string):
        """
        regex string input
        :regex_string: regex match string
        :return:
        """
        pass
