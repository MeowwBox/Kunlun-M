package test_case19a

// Case 19b: 跨文件封装 sink - main 文件
// 调用 19a 中的封装函数，参数来自可控源 os.Args

import (
	"fmt"
	"os"
)

func main() {
	userInput := os.Args[1]
	// 调用跨文件封装函数
	result := ExecuteCommand(userInput)
	fmt.Println(result)
}
