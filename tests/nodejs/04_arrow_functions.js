/**
 * 场景 4: 箭头函数（ArrowFunctionExpression）
 * Express 路由使用箭头函数回调
 * 预期：如果引擎支持 ArrowFunctionExpression 则检出，否则可能漏报
 */
var { exec, execSync } = require('child_process');
var express = require('express');
var app = express();

// 箭头函数路由回调
app.get('/arrow1', (req, res) => {
    var cmd = req.query.cmd;
    exec(cmd, (err, stdout) => {
        res.send(stdout);
    });
});

// 混合：普通函数 + 箭头函数
app.get('/arrow2', function(req, res) {
    var input = req.query.input;
    var handler = (data) => {
        exec(data);
    };
    handler(input);
});

// 箭头函数赋值给变量后调用
var runCmd = (cmd) => execSync(cmd);

app.get('/arrow3', (req, res) => {
    var result = runCmd(req.query.cmd);
    res.send(result);
});

app.listen(3000);
