/*
 * Case 29a: C NewFunction - 多 sink 封装 (命令注入 + 路径穿越 + 格式化字符串)
 * 一个 utils 文件封装了多种不同类型的 sink
 * 预期: NewCore 二次扫描检出多个 CVI
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* 命令执行封装 */
void runCommand(const char *cmd) {
    system(cmd);
}

/* 文件读取封装 */
void loadFile(const char *path) {
    char buf[1024];
    FILE *f = fopen(path, "r");
    if (f) {
        fread(buf, 1, sizeof(buf), f);
        fclose(f);
    }
}

/* 格式化字符串封装 */
void formatOutput(const char *fmt) {
    char buf[256];
    sprintf(buf, fmt);
    printf("%s\n", buf);
}
