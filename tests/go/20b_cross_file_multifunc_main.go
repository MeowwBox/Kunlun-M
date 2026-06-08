package test_case20a

// Case 20b: 多层函数调用封装 - main 文件
// 调用 processInput，参数来自 os.Args

import (
	"fmt"
	"os"
)

func main() {
	cmd := os.Args[1]
	output := processInput(cmd)
	fmt.Println(output)
}
