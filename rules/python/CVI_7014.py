# -*- coding: utf-8 -*-
from utils.api import *


class CVI_7014():
    """
    Python 表达式注入
    覆盖: f-string 格式化滥用, format_map, string.Template
    """
    def __init__(self):
        self.svid = 7014
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "表达式注入"
        self.description = "用户输入可能被用于字符串格式化，存在格式化字符串攻击风险"
        self.level = 5
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"\.format_map|\.format\(|string\.Template|\.substitute\(|\.safe_substitute\("
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = ["format_map", "format", "Template", "substitute", "safe_substitute"]

    def main(self, regex_string):
        pass
