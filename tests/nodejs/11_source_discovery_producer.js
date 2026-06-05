/**
 * Source Discovery Benchmark - 用户自定义 source producer (JS)
 *
 * 场景：getUserInput() 内部访问 req.query，
 *       handleRequest() 调用它，最终传入 eval()。
 * 预期：Source Discovery 识别 getUserInput() 为 source producer。
 */

// 用户自定义 source producer — 内部访问 req.query
function getUserInput(req, key) {
    return req.query[key];
}

// 中间处理层
function handleRequest(req) {
    var input = getUserInput(req, 'cmd');
    return input;
}

// sink
function handler(req, res) {
    var cmd = handleRequest(req);
    eval(cmd);  // line 19 — 应检出 CVI-1004
}
