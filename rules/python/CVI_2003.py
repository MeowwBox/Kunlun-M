# -*- coding: utf-8 -*-
from utils.api import *


class CVI_2003():
    def __init__(self):
        self.svid = 2003
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "反序列化"
        self.description = "使用了可能存在反序列化漏洞的危险函数"
        self.level = 7
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"pickle\.loads|pickle\.load|yaml\.load|yaml\.unsafe_load|yaml\.full_load|marshal\.loads|marshal\.load|shelve\.open|jsonpickle\.decode|pandas\.read_pickle"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = None

    def main(self, regex_string):
        pass
