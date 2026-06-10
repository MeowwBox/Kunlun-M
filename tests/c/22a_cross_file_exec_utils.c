/*
 * Case 22a: 跨文件封装 sink - utils 文件
 * 定义封装函数，内部调用 sink
 */

#include <stdlib.h>
#include <string.h>

/* 命令执行封装 */
void executeCommand(const char *cmd) {
    system(cmd);
}

/* 字符串拼接（SQL注入）封装 */
char *queryUser(const char *name) {
    char buf[256];
    sprintf(buf, "SELECT * FROM users WHERE name = %s", name);
    return strdup(buf);
}

/* 文件读取封装 */
void readFile(const char *path) {
    char buf[1024];
    FILE *f = fopen(path, "r");
    if (f) {
        fread(buf, 1, sizeof(buf), f);
        fclose(f);
    }
}
