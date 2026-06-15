package test_case36

// Case 36: 开放重定向 - http.Redirect 使用硬编码相对路径（不应检出）

import (
	"net/http"
)

func handler(w http.ResponseWriter, r *http.Request) {
	// 安全：硬编码的相对路径
	http.Redirect(w, r, "/login", http.StatusFound)
}
