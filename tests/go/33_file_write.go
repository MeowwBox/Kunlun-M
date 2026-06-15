package test_case33

// Case 33: 任意文件写入 - os.WriteFile 使用用户输入路径（应该检出）

import (
	"os"
)

func main() {
	userInput := os.Args[1]

	// 危险：用户控制文件写入路径
	os.WriteFile(userInput, []byte("data"), 0644)
}
