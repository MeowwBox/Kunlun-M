#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 命令注入 - snprintf 构造命令再执行（指针参数写入）
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    char cmd[256];
    snprintf(cmd, sizeof(cmd), "ping %s", argv[1]);
    system(cmd);
    return 0;
}
