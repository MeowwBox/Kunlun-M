#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 格式化字符串 - argv 直接传入 printf
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    printf(argv[1]);
    return 0;
}
