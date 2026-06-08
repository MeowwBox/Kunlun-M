/**
 * 场景 16a: 跨文件追踪 - 负面用例（安全封装）
 * utils 模块导出的函数内部没有危险 sink
 */
function safeToUpper(str) {
    return String(str).toUpperCase();
}

function safeConcat(a, b) {
    return a + b;
}

module.exports = {
    safeToUpper: safeToUpper,
    safeConcat: safeConcat
};
