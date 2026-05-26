# -*- coding: utf-8 -*-
from utils.api import *


class CVI_2001():
    def __init__(self):
        self.svid = 2001
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "代码执行"
        self.description = "使用了可能执行动态代码的函数，可能导致代码注入"
        self.level = 8
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"eval|exec|compile|__import__"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = None

    def main(self, regex_string):
        pass
