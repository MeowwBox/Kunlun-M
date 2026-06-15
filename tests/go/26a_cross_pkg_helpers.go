package helpers

// Case 26a: Go 跨包 import - helpers 包
import (
	"os/exec"
)

// ExecuteCommand 封装了 exec.Command
func ExecuteCommand(cmd string) string {
	out, _ := exec.Command("sh", "-c", cmd).Output()
	return string(out)
}

// SanitizeCommand 对命令做安全处理
func SanitizeCommand(cmd string) string {
	var safe []byte
	for _, c := range cmd {
		if (c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') || c == ' ' {
			safe = append(safe, byte(c))
		}
	}
	return string(safe)
}
