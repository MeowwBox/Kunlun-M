# -*- coding: utf-8 -*-
from utils.api import *


class CVI_2007():
    def __init__(self):
        self.svid = 2007
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "信息泄露"
        self.description = "存在可能导致敏感信息泄露的调试或错误处理配置"
        self.level = 3
        self.status = True
        self.match_mode = "only-regex"
        self.match = r"DEBUG\s*=\s*True|app\.run\(.*debug\s*=\s*True|traceback\.print_exc|sys\.exc_info"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = None

    def main(self, regex_string):
        pass
