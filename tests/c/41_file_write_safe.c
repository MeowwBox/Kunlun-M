/*
 * Case 41: C 任意文件写入 - 硬编码路径（不应检出）
 */

#include <stdio.h>

int main() {
    // 安全：硬编码路径
    FILE *fp = fopen("/tmp/fixed_file.txt", "w");
    if (fp) {
        fprintf(fp, "data");
        fclose(fp);
    }
    return 0;
}
