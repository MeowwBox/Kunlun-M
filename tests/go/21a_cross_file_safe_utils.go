package test_case21a

// Case 21a: 安全封装 - 负面用例
// 封装函数内部做了安全处理

import (
	"strings"
	"os/exec"
)

func SafeExecuteCommand(cmd string) string {
	// 只允许字母数字
	sanitized := strings.Map(func(r rune) rune {
		if r >= 'a' && r <= 'z' || r >= 'A' && r <= 'Z' || r >= '0' && r <= '9' {
			return r
		}
		return -1
	}, cmd)
	if len(sanitized) == 0 {
		return ""
	}
	out, _ := exec.Command("sh", "-c", sanitized).Output()
	return string(out)
}
