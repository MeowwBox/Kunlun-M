# -*- coding: utf-8 -*-
"""
    demo_c
    ~~~~~
    C/C++ 修复函数和可控输入源配置

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

# 修复函数 → 可防御的 CVI 编号
C_IS_REPAIR_DEFAULT = {
    # ---- 命令注入防御 (9001) ----
    # exec 系列函数本身是安全替代（不通过 shell）：
    # execl/execlp/execle/execv/execvp/execve 不走 shell 解析
    # 但修复函数概念上更多是"参数处理"，C 的命令注入主要靠不用 system()
    # 这里不列 exec 系列（它们本身就是 sink，不是修复函数）
    # 整型转换可防注入
    "atoi": [9001],
    "strtol": [9001],
    "strtonum": [9001],
    "snprintf": [9001],  # 格式化输出（替代 sprintf）

    # ---- 格式化字符串防御 (9002) ----
    # 使用固定格式字符串（不把用户输入当 format 参数）
    "printf": [9002],
    "fprintf": [9002],
    "sprintf": [9002],
    "snprintf": [9002],
    "vprintf": [9002],
    "vfprintf": [9002],
    "vsprintf": [9002],
    "vsnprintf": [9002],
    "syslog": [9002],

    # ---- 缓冲区溢出防御 (9003) ----
    # 长度受限的字符串操作
    "strncpy": [9003],
    "strlcpy": [9003],
    "strlcat": [9003],
    "strncat": [9003],
    "snprintf": [9003],
    "fgets": [9003],
    "getline": [9003],

    # ---- 路径穿越防御 (9004) / 文件读取防御 (9007) ----
    "basename": [9004, 9007],
    "dirname": [9004, 9007],
    "realpath": [9004, 9007],

    # ---- 整数溢出防御 (9005) ----
    "strtol": [9005],
    "strtoul": [9005],
    "strtoll": [9005],
    "strtoull": [9005],
    "sscanf": [9005],
    "strtof": [9005],
    "strtod": [9005],

    # ---- 环境变量防御 (9006) ----
    # 使用 secure_getenv（setuid 安全）
    "secure_getenv": [9006],
}

# 可控输入源
C_IS_CONTROLLED_DEFAULT = [
    # 标准输入
    "stdin",
    "scanf",
    "fscanf",
    "fgets",
    "getline",
    "gets",
    "read",
    "fread",
    # 命令行参数
    "argv",
    "argc",
    # 环境变量
    "getenv",
    # 网络
    "recv",
    "recvfrom",
    "recvmsg",
    "fgetc",
    # 配置文件读取
    "fopen",
    "fdopen",
    # CGI
    "getenv",
    "getenv(\"REQUEST_METHOD\")",
    "getenv(\"QUERY_STRING\")",
    "getenv(\"CONTENT_LENGTH\")",
    "getenv(\"REMOTE_ADDR\")",
    "getenv(\"HTTP_REFERER\")",
    "getenv(\"HTTP_COOKIE\")",
    "getenv(\"HTTP_USER_AGENT\")",
]
