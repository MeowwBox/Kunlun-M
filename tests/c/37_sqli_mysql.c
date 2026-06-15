/*
 * Case 37: C SQL注入 - mysql_query 字符串拼接（应该检出）
 */

#include <stdio.h>
#include <mysql/mysql.h>

int main(int argc, char *argv[]) {
    MYSQL *conn;
    char query[512];

    // 危险：用户输入拼接到 SQL
    sprintf(query, "SELECT * FROM users WHERE name = '%s'", argv[1]);
    mysql_query(conn, query);

    return 0;
}
