# -*- coding: utf-8 -*-
from utils.api import *


class CVI_7010():
    """
    Python LDAP 注入
    覆盖: ldap3, python-ldap 的搜索操作
    """
    def __init__(self):
        self.svid = 7010
        self.language = "python"
        self.author = "LoRexxar"
        self.vulnerability = "LDAP注入"
        self.description = "LDAP搜索操作使用了可能可控的过滤条件，可能导致LDAP注入"
        self.level = 6
        self.status = True
        self.match_mode = "function-param-regex"
        self.match = r"ldap\.search\(|connection\.search\(|conn\.search\(|ldap\.search_s\(|ldap\.search_ext\(|l\.search\(|l\.search_s\(|l\.search_ext\("
        self.match_name = None
        self.black_list = None
        self.keyword = None
        self.unmatch = None
        self.vul_function = None

    def main(self, regex_string):
        pass
