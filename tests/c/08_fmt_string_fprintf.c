#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 格式化字符串 - fprintf 格式串来自 argv
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    fprintf(stderr, argv[1]);
    return 0;
}
