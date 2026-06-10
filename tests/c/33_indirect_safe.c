/**
 * Case 31: C 间接调用 - 安全场景（不应检出）
 * 将 system 赋值给函数指针，但参数是硬编码的
 */

#include <stdlib.h>
#include <stdio.h>

int main(int argc, char *argv[]) {
    // 间接调用模式，但参数是硬编码字符串，不存在注入风险
    int (*func)(const char *) = system;
    func("ls -la");

    return 0;
}
