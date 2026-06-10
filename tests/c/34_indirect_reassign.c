/**
 * Case 32: C 间接调用 - 重新赋值后安全（不应检出）
 * 先赋值为 system，后重新赋值为 printf（安全函数）
 */

#include <stdlib.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    char *cmd = argv[1];

    // 先赋值为 sink 函数
    int (*func)(const char *) = system;
    // 重新赋值为安全函数（映射应被清除）
    func = (int (*)(const char *))printf;
    // 后续调用 func 不应触发检测
    func(cmd);

    return 0;
}
