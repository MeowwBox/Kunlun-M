package test_case20a

// Case 20a: 多层函数调用封装 - utils 文件
// processInput 调用 runCommand，runCommand 调用 exec.Command

import (
	"os/exec"
)

func runCommand(cmd string) string {
	out, _ := exec.Command("sh", "-c", cmd).Output()
	return string(out)
}

func processInput(input string) string {
	return runCommand(input)
}
