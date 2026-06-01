#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 缓冲区溢出 - argv 直接 strcpy
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    char buf[64];
    strcpy(buf, argv[1]);
    return 0;
}
