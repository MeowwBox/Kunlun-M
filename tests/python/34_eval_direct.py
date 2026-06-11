#!/usr/bin/env python3
"""
Case 34: eval 直接调用 — 应检出 CVI-7001
eval(user_input) 参数直接可控
"""
import sys

user_input = sys.argv[1]
eval(user_input)
