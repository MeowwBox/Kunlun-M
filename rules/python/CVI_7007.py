# -*- coding: utf-8 -*-
from utils.api import *

class CVI_7007(SingleRuleMixin):
    """
    Python 信息泄露 / 不安全配置
    覆盖: DEBUG=True, secret_key 硬编码, traceback, 异常暴露
    """
    def __init__(self):
        self.svid = 7007
        self.language = "python"
        self.vulnerability = "信息泄露"
        self.description = "存在可能导致敏感信息泄露的调试或错误处理配置"
        self.level = 3
        self.match_mode = "only-regex"
        self.match = [r"DEBUG\s*=\s*True|app\.run\(.*debug\s*=\s*True|traceback\.print_exc|sys\.exc_info|SECRET_KEY\s*=\s*[\"'][^\"']+[\"']|ALLOWED_HOSTS\s*=\s*\[\s*[\"']\*[\"']"]

    def main(self, regex_string):
        pass
