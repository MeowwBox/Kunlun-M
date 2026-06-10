/**
 * Case 30: C 间接调用 - 函数指针赋值后调用（应该检出）
 * 将 system 赋值给函数指针，通过函数指针调用
 * 预期: 检出 CVI-9001 (命令注入)
 */

#include <stdlib.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    char *cmd = argv[1];

    // 间接调用模式：将 sink 函数赋值给函数指针
    int (*func)(const char *) = system;
    func(cmd);

    return 0;
}
