package test_case35

// Case 35: 开放重定向 - http.Redirect 使用用户输入 URL（应该检出）

import (
	"net/http"
	"os"
)

func main() {
	redirectURL := os.Args[1]
	var w http.ResponseWriter
	var r *http.Request

	// 危险：使用用户可控的输入作为重定向 URL
	http.Redirect(w, r, redirectURL, http.StatusFound)
}
