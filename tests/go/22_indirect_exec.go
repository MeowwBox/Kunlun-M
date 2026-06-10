package test_case22

// Case 22: 间接调用 - 命令注入（应该检出）
// 将 exec.Command 赋值给变量，通过变量调用

import (
	"fmt"
	"os"
	"os/exec"
)

func main() {
	userInput := os.Args[1]
	// 间接调用模式：将 sink 函数赋值给变量
	cmdFunc := exec.Command
	cmd := cmdFunc("sh", "-c", userInput)
	fmt.Println(cmd)
	_ = cmd
}
