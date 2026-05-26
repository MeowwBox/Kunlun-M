# -*- coding: utf-8 -*-
from utils.api import *


class CVI_2000():
    def __init__(self):
        self.svid = 2000
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "命令注入"
        self.description = "使用了可能执行系统命令的函数，可能导致命令注入"
        self.level = 8
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"os\.system|os\.popen|subprocess\.call|subprocess\.run|subprocess\.Popen|subprocess\.check_output|subprocess\.check_call|commands\.getoutput|commands\.getstatusoutput|exec"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = None

    def main(self, regex_string):
        pass
