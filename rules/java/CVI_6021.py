# -*- coding: utf-8 -*-
from utils.api import *

class CVI_6021(SingleRuleMixin):
    def __init__(self):
        self.svid = 6021
        self.language = "java"
        self.vulnerability = "JDBC SQL Injection (String Concatenation)"
        self.description = "通过字符串拼接构建SQL查询，参数未经参数化处理，存在SQL注入风险"
        self.level = 8
        self.match_mode = "regex-return-regex"
        self.match = [r"executeQuery\(.*?=padding="]
        self.unmatch = [r"PreparedStatement", r"prepareStatement"]
        self.match_name = r"(?:String\s+(\w+)\s*=\s*request\.(?:getParameter|getHeader|getInputStream|getReader|getQueryString|getParameterValues|getParameterMap|getCookies)\([^)]*\)|@(?:RequestParam|PathVariable|RequestHeader|CookieValue|QueryParam|FormParam)\s*(?:\([^)]*\)\s*)?String\s+(\w+))"
        self.black_list = []

    def main(self, regex_string):
        pass
