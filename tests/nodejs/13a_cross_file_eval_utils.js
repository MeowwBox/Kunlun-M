/**
 * 场景 13a: 跨文件追踪 - CommonJS require 导出 eval 封装
 * utils 模块封装了 eval 调用
 */
function evaluateExpression(expr) {
    return eval(expr);
}

function runScript(code) {
    return eval(code);
}

module.exports = {
    evaluateExpression: evaluateExpression,
    runScript: runScript
};
