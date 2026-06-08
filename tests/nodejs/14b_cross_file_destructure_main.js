/**
 * 场景 14b: 跨文件追踪 - 解构导入 { executeCmd } from require
 * 预期：跨文件检测到 executeCmd 内部的 exec sink
 */
var { executeCmd } = require('./14a_cross_file_destructure_utils');

app.get('/cmd', function(req, res) {
    var cmd = req.query.cmd;
    executeCmd(cmd);
    res.send('done');
});
