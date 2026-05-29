/**
 * 场景 8: 闭包捕获变量 + 字符串拼接
 * 污点通过闭包跨越函数边界，或通过字符串拼接传递
 * 预期：如果引擎追踪字符串拼接，则检出
 */
var { exec } = require('child_process');
var express = require('express');
var app = express();

// 闭包捕获外部变量
app.get('/closure1', function(req, res) {
    var cmd = req.query.cmd;
    function inner() {
        exec(cmd);
    }
    inner();
});

// 闭包 + setTimeout
app.get('/closure2', function(req, res) {
    var target = req.query.target;
    setTimeout(function() {
        exec('ping -c 3 ' + target);
    }, 1000);
});

// 字符串拼接
app.get('/concat1', function(req, res) {
    var host = req.query.host;
    var cmd = 'nslookup ' + host;
    exec(cmd);
});

// 模板字符串
app.get('/template1', function(req, res) {
    var name = req.query.name;
    var cmd = `echo "Hello ${name}"`;
    exec(cmd);
});

// 数组拼接
app.get('/array1', function(req, res) {
    var args = req.query.args;
    var parts = ['git', 'log', args];
    var cmd = parts.join(' ');
    exec(cmd);
});

app.listen(3000);
