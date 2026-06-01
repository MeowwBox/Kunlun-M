#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 缓冲区溢出 - gets 函数（无论参数都应报）
int main() {
    char buf[64];
    gets(buf);
    printf("Input: %s\n", buf);
    return 0;
}
