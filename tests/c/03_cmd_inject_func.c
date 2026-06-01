#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 命令注入 - 多函数传递：argv -> 函数参数 -> system
void execute_command(const char *cmd) {
    system(cmd);
}

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    execute_command(argv[1]);
    return 0;
}
