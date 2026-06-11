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

class CVI_3002(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):

        self.svid = 3002
        self.language = "javascript"
        self.vulnerability = "XSS"
        self.description = "可控内容被直接写入页面内，会导致XSS漏洞"
        self.level = 5

        # 部分配置
        self.match_mode = "function-param-regex"
        self.match = r"document.write|document.writeln"

    def main(self, regex_string):
        """
        regex string input
        :regex_string: regex match string
        :return:
        """
        pass
