package test_case29

// Case 29: XXE - xml.Unmarshal 解析不可信数据（应该检出）

import (
	"encoding/xml"
	"os"
)

func main() {
	userInput := os.Args[1]

	// 危险：直接反序列化不可信的 XML 数据
	var result interface{}
	err := xml.Unmarshal([]byte(userInput), &result)
	_ = err
	_ = result
}
