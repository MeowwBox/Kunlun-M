/*
 * Case 28b: C NewFunction - 主文件使用封装函数返回值 (命令注入 + 溢出)
 * 调用 28a 中的 readInput 获取返回值，传给 strcpy 和 system
 * 预期: NewCore 二次扫描后检出 CVI-9001 (system) / CVI-9003 (strcpy)
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern char* readInput();

int main(int argc, char *argv[]) {
    char *data = readInput();
    char cmd[128];
    strcpy(cmd, data);
    system(cmd);
    return 0;
}
