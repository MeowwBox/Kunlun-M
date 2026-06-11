# -*- coding: utf-8 -*-
"""
    api
    ~~~

    公共工具导入 + CVI 规则基类

    :author:    LoRexxar <LoRexxar@gmail.com>
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
"""

import os
import re
import requests

from utils.log import logger


class SingleRuleMixin:
    """
    CVI 规则基类 Mixin，提供所有字段的默认值。

    使用方式：
        class CVI_XXXX(SingleRuleMixin):
            def __init__(self):
                self.svid = XXXX
                self.language = "python"
                # 其他字段使用基类默认值即可
                # 如需自定义修复函数：
                self.extra_repair_functions = ['my_sanitize']

    基类保证即使规则漏写字段也不会 AttributeError，提高鲁棒性。
    """

    # --- 必须由子类覆盖的字段 ---
    svid = None
    language = None

    # --- 核心匹配字段（子类通常需覆盖）---
    vulnerability = "Unknown"
    description = ""
    level = 0
    status = True
    match_mode = "function-param-regex"
    match = None
    match_name = None
    vul_function = None

    # --- 过滤/排除字段（默认 None = 不过滤）---
    unmatch = None
    black_list = None
    keyword = None

    # --- 元信息字段（默认值合理，子类可选覆盖）---
    author = "Kunlun-M"

    # --- 三层修复函数体系 ---
    # L3: 规则级自定义修复函数列表（由 filter_functions 机制加载）
    # 为空则只使用 L1(builtin) + L2(summary)
    extra_repair_functions = []

    # --- NewCore 二次筛选 ---
    # 框架特征匹配（用于框架识别）
    framework_deps = []
    # 配置型漏洞参数模式（用于规则 main() 中的二次筛选）
    config_patterns = None
    config_vuln_args = None
    is_config_vuln = None
    is_eval_object = None
    exclude_patterns = None


__all__ = (
    're', 'os', 'requests', 'logger',
    'SingleRuleMixin',
)
