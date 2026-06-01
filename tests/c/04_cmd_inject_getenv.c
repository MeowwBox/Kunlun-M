#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 命令注入 - getenv 作为可控源
int main() {
    char *cmd = getenv("CMD");
    if (cmd != NULL) {
        system(cmd);
    }
    return 0;
}
