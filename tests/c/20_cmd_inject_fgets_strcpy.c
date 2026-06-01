#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 命令注入 - fgets + strcpy 中间传递
int main() {
    char input[256], cmd[256];
    fgets(input, sizeof(input), stdin);
    strcpy(cmd, input);
    system(cmd);
    return 0;
}
