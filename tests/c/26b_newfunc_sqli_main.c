/*
 * Case 26b: C NewFunction - 主文件调用封装函数 (格式化字符串)
 * 调用 26a 中的 logMessage，参数来自 getenv
 * 预期: NewCore 二次扫描后检出 CVI-9002 (sprintf)
 */

#include <stdio.h>
#include <stdlib.h>

extern void logMessage(const char *user_input);

int main(int argc, char *argv[]) {
    char *input = getenv("USER_INPUT");
    logMessage(input);
    return 0;
}
