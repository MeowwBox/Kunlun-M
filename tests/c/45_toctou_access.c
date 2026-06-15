/*
 * Case 45: C 竞态条件(TOCTOU) - access() 后跟 open()（应该检出）
 */

#include <unistd.h>
#include <fcntl.h>

int main(int argc, char *argv[]) {
    // 危险：先检查再使用模式（TOCTOU）
    if (access(argv[1], R_OK) == 0) {
        int fd = open(argv[1], O_RDONLY);
        // 在 access 和 open 之间，文件可能被替换
        close(fd);
    }
    return 0;
}
