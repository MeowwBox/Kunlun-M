#!/usr/bin/env python
# -*- coding: utf-8 -*-
import re
from utils.log import logger


def init_match_rule(data):
    """
    处理 Java 新生成规则初始化正则匹配

    :param data: NewFunction chain 中的 source tuple (func_name, param_name, vul_function)
                或 code=5 的 dict {'code': 5, 'source': ('func_name', 'param_name', 'vul_function'), ...}
    :return: (match, match2, vul_function, index, origin_func_name)
    """
    obj = data[0]

    # code=5: data[0] 是 dict {'code': 5, 'source': ('func_name', 'param_name', 'vul_function'), ...}
    if isinstance(obj, dict) and 'source' in obj:
        source = obj['source']
        function_name = source[0]  # 封装函数名（可能带类名前缀）
        origin_func_name = function_name

        match = r"(?:^|[\s=,.])" + re.escape(function_name) + r"\s*\([^)]*\)"
        if '.' in function_name:
            # 带类名限定符（如 ExecUtils.executeCommand）
            # Java 方法定义不包含类名前缀，grep 不会误匹配定义行，无需 match2
            match2 = None
        else:
            # 纯方法名（如 executeCommand）
            match2 = r"(?:public|private|protected|static|abstract|final|synchronized|native|strictfp|volatile|transient|\s)*(?:[\w<>\[\]]+\s+)+" + re.escape(function_name) + r"\s*\("
        logger.debug("[New Rule] Java match (from code=5): {}".format(match))
        return match, match2, function_name, 0, origin_func_name

    if isinstance(obj, str):
        function_name = obj
        origin_func_name = function_name

        match = r"(?:^|[\s=,.])" + re.escape(function_name) + r"\s*\([^)]*\)"
        if '.' in function_name:
            match2 = None
        else:
            match2 = r"(?:public|private|protected|static|abstract|final|synchronized|native|strictfp|volatile|transient|\s)*(?:[\w<>\[\]]+\s+)+" + re.escape(function_name) + r"\s*\("
        logger.debug("[New Rule] Java match: {}".format(match))
        return match, match2, function_name, 0, origin_func_name

    logger.debug("[New Rule] Java auto rule generation: unsupported data type")
    return None, None, None, 0, "None"
