# -*- coding: utf-8 -*-
from utils.api import *


class CVI_2002():
    def __init__(self):
        self.svid = 2002
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "SQL注入"
        self.description = "使用了可能存在SQL注入风险的数据库操作函数"
        self.level = 7
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"execute|cursor\.execute"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = ["execute", "cursor.execute"]

    def main(self, regex_string):
        pass
