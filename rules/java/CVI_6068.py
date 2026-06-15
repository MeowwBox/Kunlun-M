# -*- coding: utf-8 -*-
from utils.api import *

class CVI_6068(SingleRuleMixin):
    """
    Commons FileUpload ≤1.3.2 反序列化 RCE
    """
    def __init__(self):
        self.svid = 6068
        self.language = "java"
        self.vulnerability = "Commons FileUpload 反序列化 RCE"
        self.level = 8
        self.description = "Commons FileUpload ≤1.3.2 DiskFileItem 可被利用触发反序列化(CVE-2016-1000031)"

        self.match_mode = "framework-dependency"
        self.match = None

        self.framework_deps = [
            {
                "group_id": "commons-fileupload",
                "artifact_id": "commons-fileupload",
                "version_range": "<=1.3.2",
                "cve": "CVE-2016-1000031",
                "description": "Commons FileUpload DiskFileItem 反序列化",
            },
        ]

        self.config_patterns = []
        self.exclude_patterns = []

        self.main = None
