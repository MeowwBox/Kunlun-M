/**
 * 场景 3: 嵌套回调（回调地狱）
 * 多层嵌套 FunctionExpression，污点从最外层传入
 * 预期：CVI-3100 命令注入
 */
var { exec } = require('child_process');
var express = require('express');
var app = express();

// 三层嵌套回调
app.get('/nested', function(req, res) {
    var userInput = req.query.cmd;

    setTimeout(function() {
        var step1 = userInput.trim();

        process.nextTick(function() {
            var step2 = step1.toLowerCase();

            exec(step2, function(err, stdout) {
                res.send(stdout);
            });
        });
    }, 100);
});

// Promise 链式回调
app.get('/promise', function(req, res) {
    var cmd = req.query.cmd;

    new Promise(function(resolve) {
        resolve(cmd);
    }).then(function(data) {
        exec(data);
        res.send('done');
    });
});

app.listen(3000);
