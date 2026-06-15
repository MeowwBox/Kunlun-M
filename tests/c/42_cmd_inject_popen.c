/*
 * Case 42: C 命令注入 - popen 使用用户输入（应该检出）
 */

#include <stdio.h>

int main(int argc, char *argv[]) {
    char cmd[256];

    // 危险：popen 执行包含用户输入的命令
    sprintf(cmd, "cat %s", argv[1]);
    FILE *fp = popen(cmd, "r");
    pclose(fp);

    return 0;
}
