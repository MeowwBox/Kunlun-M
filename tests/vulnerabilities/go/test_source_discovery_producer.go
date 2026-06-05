package test_source_discovery

// Source Discovery Benchmark - 用户自定义 source producer (Go)
//
// 场景：getUserInput() 内部访问 r.URL.Query()，
//       handler 直接调用 getUserInput()，传入 exec.Command。
// 预期：Source Discovery 识别 getUserInput() 为 source producer。

import (
	"net/http"
	"os/exec"
)

// 用户自定义 source producer — 内部访问 r.URL.Query()
func getUserInput(r *http.Request, key string) string {
	return r.URL.Query().Get(key)
}

// handler — sink，直接调用 source producer
func handler(w http.ResponseWriter, r *http.Request) {
	cmd := getUserInput(r, "cmd")
	exec.Command("sh", "-c", cmd).Run() // 应检出 CVI-8001
}
