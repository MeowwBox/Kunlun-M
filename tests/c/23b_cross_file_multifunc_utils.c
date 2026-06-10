/*
 * Case 23b: 多层函数调用封装 - 底层 utils
 * runCommand 直接调用 system
 */

#include <stdlib.h>

/* 底层封装 */
void runCommand(const char *cmd) {
    system(cmd);
}
