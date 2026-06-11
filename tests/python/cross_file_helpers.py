"""
跨文件追踪辅助模块
提供 sanitize 函数，内部调用 html.escape（builtin safe 函数）
提供 passthrough 函数，直接返回数据
"""

def sanitize(data):
    """对数据进行 HTML 转义 — 应被判定为修复函数"""
    return html.escape(data)

def passthrough(data):
    """直接返回数据 — 应被判定为透传"""
    return data
