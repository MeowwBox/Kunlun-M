/*
 * Case 44: C 命令注入 - 硬编码命令（不应检出）
 */

#include <stdio.h>
#include <stdlib.h>

int main() {
    // 安全：硬编码命令
    system("ls -la");
    return 0;
}
