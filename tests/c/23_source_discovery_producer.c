#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Source Discovery Benchmark - 用户自定义 source producer (C)
 *
 * 场景：read_user_input() 内部调用 fgets(stdin)，
 *       main 直接调用 read_user_input()，传入 system()。
 * 预期：Source Discovery 识别 read_user_input() 为 source producer。
 */

// 用户自定义 source producer — 内部调用 fgets
char* read_user_input() {
    static char buf[256];
    fgets(buf, sizeof(buf), stdin);
    return buf;
}

// sink — 直接调用 source producer
int main() {
    system(read_user_input());  // 应检出 CVI-1001
    return 0;
}
