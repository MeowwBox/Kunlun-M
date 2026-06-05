#include <stdio.h>
#include <stdlib.h>

/*
 * Source Discovery Benchmark - source producer 区分 (C)
 *
 * 场景：get_safe_value() 返回硬编码值，read_env_config() 调用 getenv。
 *       只有 read_env_config 路径应被检出。
 */

// 安全函数 — 不访问任何 source
const char* get_safe_value() {
    return "hardcoded";
}

// 用户自定义 source producer — 调用 getenv
char* read_env_config(const char* key) {
    char* val = getenv(key);
    return val;
}

// 混合使用
int main() {
    const char* safe = get_safe_value();
    char* config = read_env_config("PATH");

    printf(safe);    // line 22 — 不应检出
    printf(config);  // line 23 — 应检出 CVI-1002
    return 0;
}
