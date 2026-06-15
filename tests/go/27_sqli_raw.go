package test_case27

// Case 27: SQL注入 - db.Query 字符串拼接（应该检出）
// 使用 fmt.Sprintf 拼接用户输入到 SQL 查询

import (
	"database/sql"
	"fmt"
	"os"
)

func main() {
	userInput := os.Args[1]
	var db *sql.DB

	// 危险：db.Query 使用字符串拼接
	rows, err := db.Query(fmt.Sprintf("SELECT * FROM users WHERE id = %s", userInput))
	_ = rows
	_ = err
}
