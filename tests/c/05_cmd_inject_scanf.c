#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 命令注入 - scanf 读取用户输入后执行
int main() {
    char cmd[256];
    scanf("%255s", cmd);
    system(cmd);
    return 0;
}
