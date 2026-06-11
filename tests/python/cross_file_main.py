"""
跨文件 import 追踪测试
场景1: sanitize 是修复函数，cmd = sanitize(user_input) → os.system(cmd) 应标记为已修复 (不检出)
场景2: passthrough 透传，data = passthrough(user_input) → eval(data) 应检出 (可控)
"""

import sys
from cross_file_helpers import sanitize, passthrough

if __name__ == '__main__':
    user_input = sys.argv[1]
    # 场景1: 修复后使用 → os.system(cmd) 不应检出（cmd 经过 sanitize 处理）
    cmd = sanitize(user_input)
    import os
    os.system(cmd)
    # 场景2: 透传后使用 → eval(data) 应检出
    data = passthrough(user_input)
    eval(data)
