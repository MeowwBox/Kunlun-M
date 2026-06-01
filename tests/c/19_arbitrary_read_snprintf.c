#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <unistd.h>

// 任意文件读取 - snprintf 构造路径再 open
int main(int argc, char *argv[]) {
    if (argc < 2) return 1;
    char filepath[256];
    snprintf(filepath, sizeof(filepath), "/etc/config/%s", argv[1]);
    int fd = open(filepath, O_RDONLY);
    if (fd >= 0) close(fd);
    return 0;
}
