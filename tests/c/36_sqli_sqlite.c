/*
 * Case 36: C SQL注入 - sqlite3_exec 字符串拼接（应该检出）
 * 使用 sprintf 拼接用户输入到 SQL 查询
 */

#include <stdio.h>
#include <string.h>
#include <sqlite3.h>

int main(int argc, char *argv[]) {
    sqlite3 *db;
    char *errMsg = NULL;
    char sql[512];

    // 危险：sprintf 拼接用户输入到 SQL
    sprintf(sql, "SELECT * FROM users WHERE id = %s", argv[1]);

    sqlite3_exec(db, sql, NULL, NULL, &errMsg);
    return 0;
}
