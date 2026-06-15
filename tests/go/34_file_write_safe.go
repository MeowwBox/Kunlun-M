package test_case34

// Case 34: 任意文件写入 - os.WriteFile 使用硬编码路径（不应检出）

import (
	"os"
)

func main() {
	// 安全：硬编码路径
	os.WriteFile("/tmp/fixed_file.txt", []byte("data"), 0644)
}
