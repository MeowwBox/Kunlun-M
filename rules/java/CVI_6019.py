# -*- coding: utf-8 -*-

"""
    Java Insecure CORS Rule
    ~~~~
    :author:    KunLun-M
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""

from utils.api import *

class CVI_6019(SingleRuleMixin):
    """
    rule class
    """

    def __init__(self):
        self.svid = 6019
        self.language = "java"
        self.vulnerability = "Insecure CORS"
        self.description = "Access-Control-Allow-Origin响应头设置为通配符*，允许任意域名的跨域请求，可能导致敏感数据泄露。"
        self.level = 4

        # 部分配置
        self.match_mode = "only-regex"
        self.match = [
            r'(?:setHeader|addHeader)\s*\(\s*"Access-Control-Allow-Origin"\s*,\s*"\*"\s*\)',
            r'@CrossOrigin\s*\(\s*(?:origins|value)\s*=\s*"\*"',
            r'\.allowedOrigins\s*\(\s*"\*"\s*\)',
        ]

        # for regex
        self.unmatch = [r"allowedOriginPatterns", r"Access-Control-Allow-Credentials"]

    def main(self, regex_string):
        pass
