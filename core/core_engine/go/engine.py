#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Go Engine — Go 自动规则生成引擎
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    :author:    LoRexxar <LoRexxar@gmail.com>
    :homepage:  https://github.com/LoRexxar/Kunlun-M
    :license:   MIT, see LICENSE for more details.
    :copyright: Copyright (c) 2017 LoRexxar. All rights reserved
"""
import re
from utils.log import logger


def init_match_rule(data):
    """
    处理 Go 新生成规则初始化正则匹配
    """
    obj = data[0]

    if isinstance(obj, str):
        # NewCore 二次扫描：data = (func_name, param_name, vul_function)
        function_name = obj
        origin_func_name = function_name
        # strip pkg prefix: pkg.Func → Func
        if '.' in function_name:
            function_name = function_name.split('.')[-1]
        # 匹配 pkg.Func(...) 和 Func(...)
        match = (r"(?:^|[\s=,.])\w+\." + re.escape(function_name) + r"\s*\([^)]*\)" +
                 r"|" +
                 r"(?:^|[\s=,])" + re.escape(function_name) + r"\s*\([^)]*\)")
        # 匹配函数定义（排除 pkg 前缀）
        match2 = r"func\s+" + re.escape(function_name) + r"\b"
        logger.debug("[New Rule] Go match: {}".format(match))
        return match, match2, function_name, 0, origin_func_name

    # AST 节点输入（预留）
    if hasattr(obj, 'type'):
        pass

    logger.debug("[New Rule] Go auto rule generation: unsupported data type")
    return None, None, None, 0, "None"
