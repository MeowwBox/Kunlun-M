/**
 * 场景 13b: 跨文件追踪 - 主文件通过 require 引入封装的 eval
 * 预期：CVI-3003 eval RCE（跨文件检测）
 */
var utils = require('./13a_cross_file_eval_utils');

app.get('/eval', function(req, res) {
    var expr = req.query.expr;
    var result = utils.evaluateExpression(expr);
    res.send(result);
});
