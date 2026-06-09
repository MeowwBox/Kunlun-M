/*
 * Case 23c: 多层函数调用封装 - main 入口
 * 调用 processInput，参数来自 argv
 */

#include <stdio.h>

extern void processInput(const char *input);

int main(int argc, char *argv[]) {
    processInput(argv[1]);
    return 0;
}
