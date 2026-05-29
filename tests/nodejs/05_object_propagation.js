/**
 * 场景 5: 对象属性传播（MemberExpression 链）
 * 污点通过对象属性传递：req.body.xxx → 中间变量 → sink
 * 预期：CVI-3100 命令注入 / CVI-3102 SSRF
 */
var { exec } = require('child_process');
var http = require('http');
var express = require('express');
var app = express();

app.use(express.json());

// 对象属性直接传递
app.post('/obj1', function(req, res) {
    var cmd = req.body.command;
    exec(cmd);
});

// 多层属性传递
app.post('/obj2', function(req, res) {
    var url = req.body.data.targetUrl;
    http.get(url, function(resp) {
        res.send('proxied');
    });
});

// 通过中间对象传递
app.post('/obj3', function(req, res) {
    var params = req.body;
    var cmd = params.cmd;
    var sanitized = cmd.toLowerCase();
    exec(sanitized);
});

// 对象解构（ES6 destructuring）
app.post('/obj4', function(req, res) {
    var { command: cmd } = req.body;
    exec(cmd);
});

app.listen(3000);
