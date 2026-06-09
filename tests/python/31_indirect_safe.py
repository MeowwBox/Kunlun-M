#!/usr/bin/env python3
"""
Case 31: Python 间接调用 - 安全场景 (硬编码参数)
func = globals().get('os.system'); func('ls -la')
预期: 不应检出 (参数是硬编码字符串)
"""
import os

func = globals().get('os.system')

# 参数是硬编码字符串，不是用户输入
func('ls -la')
