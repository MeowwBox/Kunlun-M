/**
 * 场景 6: Express 中间件链式传播
 * 污点通过中间件赋值到 req 对象上，在后续路由中使用
 * 预期：如果能追踪 req 上的自定义属性，则检出
 */
var { exec } = require('child_process');
var express = require('express');
var app = express();

// 中间件：在 req 上挂载用户输入
app.use(function(req, res, next) {
    req.userCmd = req.query.cmd;
    req.userData = req.query.data;
    next();
});

// 路由中使用中间件挂载的数据
app.get('/mw1', function(req, res) {
    exec(req.userCmd);
});

app.get('/mw2', function(req, res) {
    var data = req.userData;
    var cmd = 'echo ' + data;
    exec(cmd);
});

// 中间件中的直接危险操作
app.use(function(req, res, next) {
    var userInput = req.query.log;
    exec(userInput);
    next();
});

app.get('/safe', function(req, res) {
    res.send('ok');
});

app.listen(3000);
