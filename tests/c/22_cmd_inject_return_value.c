#include <stdio.h>
#include <stdlib.h>
#include <string.h>

// 命令注入 - 通过函数返回值传递
char* get_user_input() {
    static char buf[256];
    fgets(buf, sizeof(buf), stdin);
    return buf;
}

int main() {
    system(get_user_input());
    return 0;
}
