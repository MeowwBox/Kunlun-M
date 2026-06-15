#include <stdlib.h>
#include <string.h>

// 多层间接调用测试
void (*func)(const char *) = system;  // 第一层：函数指针赋值
void (*func2)(const char *) = func;    // 第二层：传递
int main(int argc, char *argv[]) {
    func2(argv[1]);   // 第三层：间接调用，应检出命令注入
    return 0;
}
