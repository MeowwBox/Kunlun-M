#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 命令注入 - 多层函数传递 argv -> A -> B -> system
void run_cmd(const char *cmd) {
    system(cmd);
}

void execute(const char *input) {
    run_cmd(input);
}

int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    execute(argv[1]);
    return 0;
}
