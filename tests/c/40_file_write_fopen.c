/*
 * Case 40: C 任意文件写入 - fopen("w") 使用用户输入（应该检出）
 */

#include <stdio.h>

int main(int argc, char *argv[]) {
    // 危险：用户控制文件路径 + 写入模式
    FILE *fp = fopen(argv[1], "w");
    if (fp) {
        fprintf(fp, "data");
        fclose(fp);
    }
    return 0;
}
