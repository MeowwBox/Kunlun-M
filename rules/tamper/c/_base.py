# -*- coding: utf-8 -*-
"""
    C/C++ base config (standard library)
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    C/C++ 修复函数和可控输入源配置（基础配置，非框架配置）

    CVI 编号对照：
    - 9001: 命令注入 (system/popen/...)
    - 9002: 格式化字符串漏洞 (printf/fprintf/...)
    - 9003: 缓冲区溢出 (strcpy/gets/...)
    - 9004: 路径穿越 (open/fopen/...)
    - 9005: 整数溢出 (malloc/alloc/...)
    - 9006: 环境变量注入 (setenv/putenv/...)
    - 9007: 任意文件读取 (fread/read/...)

    :author:    Kunlun-M
    :license:   MIT, see LICENSE for more details.
"""

# NOTE: C 语言的 repair_dict 和 controlled_list 在旧版 init_php_repair 中
# 始终为空字典/空列表。这里保留空值以维持兼容行为。
# 待后续 Phase 2 评估后再逐步启用。
IS_REPAIR = {}

IS_CONTROLLED = []
