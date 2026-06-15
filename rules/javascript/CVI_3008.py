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

class CVI_3008(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):

        self.svid = 3008
        self.language = "javascript"
        self.vulnerability = "Chrome ext function XSS"
        self.description = "Chrome ext function XSS，chrome插件独有的XSS漏洞"
        self.level = 4

        # 部分配置
        self.match_mode = "function-param-regex"
        self.match = r"chrome.tabs.update|chrome.tabs.executeScript"

    def main(self, regex_string):
        """
        regex string input
        :regex_string: regex match string
        :return:
        """
        pass
