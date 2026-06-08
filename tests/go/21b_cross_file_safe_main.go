package test_case21a

// Case 21b: 安全封装 - 负面用例 main 文件

import (
	"fmt"
	"os"
)

func main() {
	input := os.Args[1]
	result := SafeExecuteCommand(input)
	fmt.Println(result)
}
