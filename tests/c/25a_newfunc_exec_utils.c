/*
 * Case 25a: C NewFunction - 封装 sink (命令注入)
 * 封装函数内部调用 system，参数是函数形参
 * 预期: NewCore 二次扫描检出 CVI-9001 (命令注入)
 */

#include <stdlib.h>

/* 命令执行封装 */
void executeCommand(const char *cmd) {
    system(cmd);
}
