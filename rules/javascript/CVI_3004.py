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

class CVI_3004(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):

        self.svid = 3004
        self.language = "javascript"
        self.vulnerability = "URL Redirect"
        self.description = "URL Redirect，url重定向可能导致很多潜在的安全问题"
        self.level = 3

        # 部分配置
        self.match_mode = "function-param-regex"
        self.match = r"document.location.replace|window.location.replace"

    def main(self, regex_string):
        """
        regex string input
        :regex_string: regex match string
        :return:
        """
        pass
