# -*- coding: utf-8 -*-
from utils.api import *

class CVI_6066(SingleRuleMixin):
    """
    Jackson-databind 多个反序列化 CVE
    """
    def __init__(self):
        self.svid = 6066
        self.language = "java"
        self.vulnerability = "Jackson-databind 反序列化 RCE"
        self.level = 8
        self.description = "Jackson-databind ≤2.9.9 存在多个反序列化漏洞(CVE-2019-12384等),enableDefaultTyping时风险更高"

        self.match_mode = "framework-dependency"
        self.match = None

        self.framework_deps = [
            {
                "group_id": "com.fasterxml.jackson.core",
                "artifact_id": "jackson-databind",
                "version_range": "<=2.9.9",
                "cve": "CVE-2019-12384",
                "description": "Jackson-databind 反序列化漏洞",
            },
        ]

        self.config_patterns = []
        self.exclude_patterns = []

        self.main = None
