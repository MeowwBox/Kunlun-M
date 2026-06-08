/**
 * Source Discovery Benchmark - source producer 区分 (JS)
 *
 * 场景：safeHelper() 返回硬编码值，getUserData() 访问 req.body。
 *       只有 getUserData 路径应被检出。
 */

// 安全函数 — 不访问任何 source
function safeHelper() {
    return "constant_value";
}

// 用户自定义 source producer — 访问 req.body
function getUserData(req, key) {
    return req.body[key];
}

// 混合使用
function handler(req, res) {
    var safe = safeHelper();
    var user = getUserData(req, 'name');
    console.log(safe);     // line 20 — 不应检出
    document.write(user);   // line 21 — 应检出
}
