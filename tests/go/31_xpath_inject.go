package test_case31

// Case 31: XPath注入 - xpath.Query 使用用户输入构造表达式（应该检出）

import (
	"os"

	"github.com/antchfx/xpath"
)

func main() {
	userInput := os.Args[1]

	// 危险：用户输入直接拼接到 XPath 表达式中
	expr := "//user[name='" + userInput + "']"
	nodes := xpath.Query(expr)
	_ = nodes
}
