/*
 * Case 46: C 竞态条件(TOCTOU) - access() 使用硬编码路径（不应检出）
 */

#include <unistd.h>
#include <fcntl.h>

int main() {
    // 安全：硬编码路径，TOCTOU 风险极低
    if (access("/etc/passwd", R_OK) == 0) {
        int fd = open("/etc/passwd", O_RDONLY);
        close(fd);
    }
    return 0;
}
