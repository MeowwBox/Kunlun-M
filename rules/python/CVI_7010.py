# -*- coding: utf-8 -*-
from utils.api import *

class CVI_7010(SingleRuleMixin):
    """
    Python LDAP 注入
    覆盖: ldap3, python-ldap 的搜索操作
    """
    def __init__(self):
        self.svid = 7010
        self.language = "python"
        self.vulnerability = "LDAP注入"
        self.description = "LDAP搜索操作使用了可能可控的过滤条件，可能导致LDAP注入"
        self.level = 6
        self.match_mode = "function-param-regex"
        self.match = r"ldap\.search\(|connection\.search\(|conn\.search\(|ldap\.search_s\(|ldap\.search_ext\(|l\.search\(|l\.search_s\(|l\.search_ext\("
        self.vul_function = ["search", "search_s", "search_ext"]

    def main(self, regex_string):
        pass
