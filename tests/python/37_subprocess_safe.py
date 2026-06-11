#!/usr/bin/env python3
"""
Case 37: subprocess + shlex.quote 修复 — 不应检出
subprocess.call(shlex.quote(user_input)) 参数已修复
"""
import subprocess
import shlex
import sys

user_input = sys.argv[1]
subprocess.call(shlex.quote(user_input))
