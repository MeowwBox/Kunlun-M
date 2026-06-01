#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 缓冲区溢出 - strcat 拼接用户输入
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    char buf[64] = "prefix_";
    strcat(buf, argv[1]);
    return 0;
}
