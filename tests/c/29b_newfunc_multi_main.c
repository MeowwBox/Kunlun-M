/*
 * Case 29b: C NewFunction - 主文件调用多个封装函数
 * 调用 29a 中的多个封装函数，参数分别来自 argv 和 getenv
 * 预期: NewCore 二次扫描后检出 CVI-9001(system) + CVI-9004(fopen) + CVI-9002(sprintf)
 */

#include <stdio.h>
#include <stdlib.h>

extern void runCommand(const char *cmd);
extern void loadFile(const char *path);
extern void formatOutput(const char *fmt);

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;

    /* 命令注入 - argv */
    runCommand(argv[1]);

    /* 路径穿越 - argv */
    loadFile(argv[1]);

    /* 格式化字符串 - getenv */
    char *fmt = getenv("LOG_FORMAT");
    formatOutput(fmt);

    return 0;
}
