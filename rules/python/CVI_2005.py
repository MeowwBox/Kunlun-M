# -*- coding: utf-8 -*-
from utils.api import *


class CVI_2005():
    def __init__(self):
        self.svid = 2005
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "文件操作"
        self.description = "使用了可能存在路径遍历或文件操作风险的函数"
        self.level = 6
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"open\(|os\.path\.join|shutil\.copy|shutil\.copyfile|shutil\.move|os\.remove|os\.unlink|os\.rename"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = None

    def main(self, regex_string):
        pass
