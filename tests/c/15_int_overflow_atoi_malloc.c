#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

// 整数溢出 - argv 通过 atoi 转换后 malloc
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    int size = atoi(argv[1]);
    char *buf = malloc(size);
    if (buf) free(buf);
    return 0;
}
