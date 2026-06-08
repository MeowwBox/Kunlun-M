/**
 * 场景 18a: 跨文件追踪 - setTimeout 封装（另一类 sink）
 * utils 模块封装了 setTimeout 调用
 */
function delayEval(code) {
    setTimeout(code, 0);
}

module.exports = {
    delayEval: delayEval
};
