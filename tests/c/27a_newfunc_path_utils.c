/*
 * Case 27a: C NewFunction - 封装 sink (路径穿越)
 * 封装函数内部调用 fopen 读取文件，参数是函数形参
 * 预期: NewCore 二次扫描检出 CVI-9004 (路径穿越)
 */

#include <stdio.h>

/* 文件读取封装 */
void readConfig(const char *filepath) {
    char buf[1024];
    FILE *f = fopen(filepath, "r");
    if (f) {
        fread(buf, 1, sizeof(buf), f);
        fclose(f);
    }
}
