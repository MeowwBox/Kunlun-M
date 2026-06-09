/*
 * Case 27b: C NewFunction - 主文件调用封装函数 (路径穿越)
 * 调用 27a 中的 readConfig，参数来自 argv
 * 预期: NewCore 二次扫描后检出 CVI-9004 (fopen)
 */

#include <stdio.h>

extern void readConfig(const char *filepath);

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    readConfig(argv[1]);
    return 0;
}
