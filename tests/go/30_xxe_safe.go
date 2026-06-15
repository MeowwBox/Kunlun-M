package test_case30

// Case 30: XXE - 使用安全配置的 Decoder（不应检出）

import (
	"bytes"
	"encoding/xml"
	"io"
)

func main() {
	xmlData := "<root><item>safe</item></root>"

	// 安全：使用 Strict/AutoClose 配置
	decoder := xml.NewDecoder(bytes.NewReader([]byte(xmlData)))
	decoder.Strict = true
	decoder.AutoClose = xml.HTMLAutoClose

	for {
		_, err := decoder.Token()
		if err == io.EOF {
			break
		}
	}
}
