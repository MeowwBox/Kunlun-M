/**
 * Case 30: JS 间接调用 - 变量函数调用
 * const f = require('child_process').exec; f(cmd)
 * 预期: 检出 CVI-3003 (eval/setTimeout) 或相关
 */

const cp = require('child_process');

function handleRequest(userInput) {
    // 间接调用: f 指向 eval, 参数是用户输入
    const f = eval;
    f(userInput);
}
