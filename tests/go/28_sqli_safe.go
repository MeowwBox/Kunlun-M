package test_case28

// Case 28: SQL注入 - db.Query 使用参数化查询（不应检出）

import (
	"database/sql"
	"os"
)

func main() {
	userInput := os.Args[1]
	var db *sql.DB

	// 安全：使用 ? 占位符参数化查询
	rows, err := db.Query("SELECT * FROM users WHERE id = ?", userInput)
	_ = rows
	_ = err
}
