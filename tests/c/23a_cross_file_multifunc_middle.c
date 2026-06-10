/*
 * Case 23a: 多层函数调用封装 - 中间层
 * processInput 调用 runCommand，runCommand 调用 system
 */

#include <stdlib.h>

extern void runCommand(const char *cmd);

/* 中间层封装 */
void processInput(const char *input) {
    runCommand(input);
}
