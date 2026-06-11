#!/usr/bin/env python
# encoding: utf-8
'''
@author: LoRexxar
@contact: lorexxar@gmail.com
@file: CVI_5005.py
@time: 2021/7/16 17:57
@desc:

'''

from utils.api import *

class CVI_5005(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):
        self.svid = 5005
        self.language = "base"
        self.vulnerability = "密码文件泄露"
        self.description = "密码文件不应该被放在项目代码当中。"
        self.level = 7

        # 部分配置
        self.match_mode = "file-path-regex-match"
        self.match = ['pass.txt', 'password.txt']

        # for regex
        self.unmatch = []

    def main(self, regex_string):
        """
        regex string input
        :regex_string: regex match string
        :return:
        """
        pass
