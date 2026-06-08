package test_case19a

// Case 19a: 跨文件封装 sink - utils 文件
// 定义封装函数，内部调用 sink

import (
	"os"
	"os/exec"
)

// 命令执行封装
func ExecuteCommand(cmd string) string {
	out, _ := exec.Command("sh", "-c", cmd).Output()
	return string(out)
}

// SQL 注入封装
func QueryUser(name string) string {
	return "SELECT * FROM users WHERE name = " + name
}

// 文件读取封装
func ReadConfig(path string) string {
	data, _ := os.ReadFile(path)
	return string(data)
}
