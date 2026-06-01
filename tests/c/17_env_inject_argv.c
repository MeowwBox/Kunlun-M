#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 环境变量注入 - argv 传入 putenv
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    putenv(argv[1]);
    return 0;
}
