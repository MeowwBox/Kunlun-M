# -*- coding: utf-8 -*-
from utils.api import *


class CVI_2006():
    def __init__(self):
        self.svid = 2006
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "XSS/SSTI"
        self.description = "使用了可能存在XSS或SSTI风险的模板渲染函数"
        self.level = 5
        self.status = True
        self.match_mode = "only-regex"
        self.match = r"render_template_string|Markup\(|\.safe|Template\(|jinja2\.Environment|\.mark_safe"
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = None

    def main(self, regex_string):
        pass
