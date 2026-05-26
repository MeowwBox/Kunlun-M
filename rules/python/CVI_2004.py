# -*- coding: utf-8 -*-
from utils.api import *


class CVI_2004():
    def __init__(self):
        self.svid = 2004
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "SSRF"
        self.description = "使用了可能存在SSRF风险的HTTP请求函数"
        self.level = 6
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"requests\.get|requests\.post|requests\.put|requests\.delete|requests\.head|requests\.patch|urllib\.request\.urlopen|urllib\.request\.urlretrieve|urlopen|http\.client\.HTTPConnection|http\.client\.HTTPSConnection"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = None

    def main(self, regex_string):
        pass
