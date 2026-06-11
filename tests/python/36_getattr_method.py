#!/usr/bin/env python3
"""
Case 36: getattr 间接调用类方法 — 应检出
obj = MyClass(); func = getattr(obj, 'run'); func(user_input)
"""
import sys


class MyClass:
    def run(self, cmd):
        import os
        return os.system(cmd)


user_input = sys.argv[1]
obj = MyClass()
func = getattr(obj, 'run')
func(user_input)
