#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 基础命令注入 - argv 直接传入 system
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    system(argv[1]);
    return 0;
}
