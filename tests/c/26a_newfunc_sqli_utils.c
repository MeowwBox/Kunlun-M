/*
 * Case 26a: C NewFunction - 封装 sink (格式化字符串)
 * 封装函数内部调用 sprintf 拼接用户输入到 SQL，参数是函数形参
 * 预期: NewCore 二次扫描检出 CVI-9002 (格式化字符串漏洞)
 */

#include <stdio.h>
#include <string.h>

/* 格式化字符串封装 - 将用户输入拼接到格式化字符串 */
void logMessage(const char *user_input) {
    char buf[256];
    sprintf(buf, user_input);
    printf("%s\n", buf);
}
