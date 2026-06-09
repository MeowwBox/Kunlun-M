/*
 * Case 25b: C NewFunction - 主文件调用封装函数 (命令注入)
 * 调用 25a 中的 executeCommand，参数来自 argv
 * 预期: NewCore 二次扫描后检出 CVI-9001 (system)
 */

#include <stdio.h>

extern void executeCommand(const char *cmd);

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    executeCommand(argv[1]);
    return 0;
}
