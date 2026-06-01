#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 路径穿越 - snprintf 构造路径再 fopen
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    char filepath[256];
    snprintf(filepath, sizeof(filepath), "/var/data/%s", argv[1]);
    FILE *f = fopen(filepath, "r");
    if (f) fclose(f);
    return 0;
}
