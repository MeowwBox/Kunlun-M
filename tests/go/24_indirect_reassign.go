package test_case24

// Case 24: 间接调用 - 重新赋值后安全（不应检出）
// 先赋值为 exec.Command，后重新赋值为安全函数

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	userInput := os.Args[1]
	// 先赋值为 sink 函数
	f := exec.Command
	// 重新赋值为安全函数（映射应被清除）
	f = fmt.Println
	// 后续调用 f 不应触发检测
	f(userInput)
	_ = os.Args
}
