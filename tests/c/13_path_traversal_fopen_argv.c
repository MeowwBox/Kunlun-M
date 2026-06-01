#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 路径穿越 - argv 直接传入 fopen
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    FILE *f = fopen(argv[1], "r");
    if (f) fclose(f);
    return 0;
}
