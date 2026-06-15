package test_case32

// Case 32: XPath注入 - 硬编码 XPath 表达式（不应检出）

import (
	"github.com/antchfx/xmlquery"
	"strings"
)

func main() {
	doc, _ := xmlquery.Parse(strings.NewReader(`<root><user><name>test</name></user></root>`))

	// 安全：硬编码 XPath 表达式
	nodes := xmlquery.Find(doc, "//user/name")
	_ = nodes
}
