#!/usr/bin/env python3
"""
Case 35: import + 条件调用 — 应检出 CVI-7000
from utils import process_command; process_command(user_input)
条件分支不影响可控性判定
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import process_command

user_input = sys.argv[2]

if len(user_input) > 0:
    process_command(user_input)
