package main

import (
	"os"
	"os/exec"
)

func main() {
	// 多层间接调用：exec.Command -> cmdFunc -> cmdFunc2 -> cmdFunc2(cmd)
	cmdFunc := exec.Command  // 第一层赋值
	cmdFunc2 := cmdFunc       // 第二层传递
	cmd := cmdFunc2("sh", "-c", os.Args[1])  // 第三层调用，应检出
	_ = cmd
}
