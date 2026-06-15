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

class CVI_10003(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):

        self.svid = 10003
        self.language = "php"
        self.vulnerability = "test_eval_check"
        self.description = "test_eval_check"
        self.level = 1

        # 部分配置
        self.match_mode = "function-param-regex"
        self.match = r"eval\s*\("

    def main(self, regex_string):
        return None
