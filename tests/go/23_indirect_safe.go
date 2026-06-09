package test_case23

// Case 23: 间接调用 - 安全场景（不应检出）
// 将 exec.Command 赋值给变量，但参数是硬编码的

import (
	"fmt"
	"os/exec"
)

func main() {
	// 间接调用模式，但参数是硬编码字符串，不存在注入风险
	safeFunc := exec.Command
	cmd := safeFunc("ls", "-la")
	fmt.Println(cmd)
	_ = cmd
}
