#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 误报排除测试 - 局部变量通过 argv 赋值（非漏洞路径）

int main(int argc, char *argv[]) {
    char buf[256];
    // 这是安全的 - 对固定长度的处理
    strncpy(buf, argv[1], sizeof(buf) - 1);
    buf[sizeof(buf) - 1] = '\0';

    // 安全的文件大小分配
    int size = 64;
    malloc(size);

    return 0;
}
