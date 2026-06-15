/*
 * Case 43: C 命令注入 - execve 使用用户输入（应该检出）
 */

#include <unistd.h>

int main(int argc, char *argv[]) {
    // 危险：execve 执行包含用户输入的命令
    char *args[] = {"/bin/sh", "-c", argv[1], NULL};
    execve("/bin/sh", args, NULL);

    return 0;
}
