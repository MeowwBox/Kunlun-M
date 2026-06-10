/*
 * Case 22b: 跨文件封装 sink - main 文件
 * 调用 22a 中的封装函数，参数来自可控源 getenv/argv
 */

#include <stdio.h>

extern void executeCommand(const char *cmd);
extern char *queryUser(const char *name);
extern void readFile(const char *path);

int main(int argc, char *argv[]) {
    /* 从环境变量获取用户输入 */
    char *userInput = getenv("USER_INPUT");

    /* 调用跨文件封装函数 */
    executeCommand(userInput);

    return 0;
}
