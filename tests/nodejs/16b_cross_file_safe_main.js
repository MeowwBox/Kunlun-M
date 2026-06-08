/**
 * 场景 16b: 跨文件追踪 - 负面用例（调用安全函数）
 * 预期：不应检出漏洞（safeToUpper 内部无危险 sink）
 */
var utils = require('./16a_cross_file_safe_utils');

app.get('/upper', function(req, res) {
    var name = req.query.name;
    var result = utils.safeToUpper(name);
    res.send(result);
});
