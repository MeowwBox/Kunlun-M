/*
 * Case 38: C SQL注入 - 硬编码 SQL 查询（不应检出）
 */

#include <sqlite3.h>

int main() {
    sqlite3 *db;
    char *errMsg = NULL;

    // 安全：硬编码 SQL
    sqlite3_exec(db, "SELECT * FROM users WHERE id = 1", NULL, NULL, &errMsg);

    return 0;
}
