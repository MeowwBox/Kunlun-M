#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 命令注入 - strlen(argv[1]) 赋值给变量
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    int len = strlen(argv[1]);
    char *buf = malloc(len + 1);
    strcpy(buf, argv[1]);
    system(buf);
    return 0;
}
