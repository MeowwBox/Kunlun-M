#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 误报排除测试 - 硬编码参数不应报

int main() {
    // 命令注入 - 硬编码字符串不应报
    system("ls -la");

    // 格式化字符串 - 硬编码格式串不应报
    printf("Hello World %d\n", 42);
    fprintf(stderr, "Error: %s\n", "something");

    // 缓冲区溢出 - 两个参数都硬编码不应报
    char buf[64];
    strcpy(buf, "hello");

    // 路径穿越 - 硬编码路径不应报
    fopen("/etc/hostname", "r");

    // 整数溢出 - 纯数字不应报
    malloc(1024);
    malloc(sizeof(int) * 10);

    // 环境变量注入 - 硬编码变量名（这个还是会报，因为 main 返回 None）
    // putenv("TEST=1");

    return 0;
}
