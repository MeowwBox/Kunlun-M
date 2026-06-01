#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>

// 任意文件读取 - argv 直接传入 open
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    int fd = open(argv[1], O_RDONLY);
    if (fd >= 0) close(fd);
    return 0;
}
