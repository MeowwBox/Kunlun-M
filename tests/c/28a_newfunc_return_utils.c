/*
 * Case 28a: C NewFunction - 封装返回值 (命令注入)
 * 封装函数从 stdin 读取数据并返回，main 中将返回值传给 system
 * 预期: NewCore 二次扫描检出 CVI-9001 (system) + CVI-9003 (strcpy溢出)
 */

#include <stdio.h>
#include <string.h>

/* 从 stdin 读取输入并返回 */
char* readInput() {
    static char buf[256];
    if (fgets(buf, sizeof(buf), stdin)) {
        return buf;
    }
    return NULL;
}
