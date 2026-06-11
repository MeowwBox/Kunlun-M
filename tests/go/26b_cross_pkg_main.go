package main

// Case 26b: Go 跨包 import - main 文件
import (
	"fmt"
	"os"
	"helpers"  // import 同目录 helpers 包
)

func main() {
	userInput := os.Args[1]

	// 场景1: 跨包调用危险函数 — 应检出
	_ = helpers.ExecuteCommand(userInput)

	// 场景2: 跨包调用安全函数 — 不应检出
	safeCmd := helpers.SanitizeCommand(userInput)
	fmt.Println(safeCmd)
}
