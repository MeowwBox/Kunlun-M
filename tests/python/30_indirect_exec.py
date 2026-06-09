#!/usr/bin/env python3
"""
Case 30: Python 间接调用 - globals()/getattr 动态调用
globals()['os.system'](cmd) 或 getattr(os, 'system')(cmd)
预期: 检出 CVI-7000 (命令执行)
"""
import os

def handle_request(user_input):
    # 通过 globals() 间接调用 os.system
    func = globals().get('os.system')
    if func:
        func(user_input)
