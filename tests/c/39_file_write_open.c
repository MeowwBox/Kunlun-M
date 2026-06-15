/*
 * Case 39: C 任意文件写入 - open() 带写入标志使用用户输入（应该检出）
 */

#include <fcntl.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    // 危险：用户控制文件路径 + 写入标志
    int fd = open(argv[1], O_WRONLY | O_CREAT, 0644);
    write(fd, "data", 4);
    close(fd);
    return 0;
}
