#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 格式化字符串 - sprintf 构造带用户输入的格式串
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    char buf[256];
    sprintf(buf, argv[1]);
    printf("%s\n", buf);
    return 0;
}
