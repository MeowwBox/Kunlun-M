#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 整数溢出 - getenv 作为大小参数
int main() {
    char *size_str = getenv("BUFFER_SIZE");
    if (size_str != NULL) {
        int size = atoi(size_str);
        char *buf = malloc(size);
        if (buf) free(buf);
    }
    return 0;
}
