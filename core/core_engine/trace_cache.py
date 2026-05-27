"""
追踪缓存模块

为扫描引擎提供两层缓存：
1. 内置知识库预载：语言内置函数的可控性信息，无需运行时分析
2. 运行时缓存：追踪过程中缓存已分析的变量可控性结果，避免重复计算

使用方式：
    from core.core_engine.trace_cache import TraceCache

    cache = TraceCache("python")

    # 查询缓存
    result = cache.get(file_path, var_name, lineno)

    # 写入缓存
    cache.put(file_path, var_name, lineno, result)

    # 查询内置知识库
    knowledge = cache.lookup_builtin(func_name)

    # 每次新扫描清空运行时缓存（内置知识库不受影响）
    cache.clear()
"""

from core.core_engine.builtin_knowledge import BuiltinKnowledge


class TraceCache:
    """变量追踪结果缓存，含内置知识库预载"""

    def __init__(self, language):
        """
        :param language: "python", "php", "javascript", "java"
        """
        self.language = language
        self._runtime_cache = {}  # key: (file_path, var_name, lineno) → value: (code, cp, expr_lineno)
        self._builtin = BuiltinKnowledge

    def _make_key(self, file_path, var_name, lineno):
        """生成缓存 key"""
        return (file_path, str(var_name), int(lineno))

    def get(self, file_path, var_name, lineno):
        """
        查询运行时缓存

        :return: (code, cp, expr_lineno) 或 None
        """
        key = self._make_key(file_path, var_name, lineno)
        return self._runtime_cache.get(key)

    def put(self, file_path, var_name, lineno, result):
        """
        写入运行时缓存

        :param result: (code, cp, expr_lineno)
        """
        key = self._make_key(file_path, var_name, lineno)
        self._runtime_cache[key] = result

    def lookup_builtin(self, func_name):
        """
        查询内置知识库

        :param func_name: 函数/方法名（支持 "module.func" 和 "func" 两种格式）
        :return: {"passthrough": [...], "safe": bool} 或 None
        """
        return self._builtin.lookup(self.language, func_name)

    def clear(self):
        """清空运行时缓存（内置知识库不受影响）"""
        self._runtime_cache.clear()

    @property
    def size(self):
        """当前缓存条目数"""
        return len(self._runtime_cache)

    def stats(self):
        """缓存统计信息"""
        return {
            "language": self.language,
            "runtime_entries": len(self._runtime_cache),
            "builtin_entries": len(getattr(self._builtin, self.language.upper(), {})),
        }
