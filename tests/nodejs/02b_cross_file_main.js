/**
 * 场景 2b: 跨文件调用 - 主服务
 * 通过 require 引入 utils 模块，调用其中的危险函数
 * 预期：CVI-3100 命令注入（如果引擎支持跨文件追踪）
 */
var express = require('express');
var utils = require('./02a_cross_file_utils');

var app = express();

app.get('/run', function(req, res) {
    var cmd = req.query.cmd;
    utils.runCommand(cmd).then(function(output) {
        res.send(output);
    });
});

app.get('/read', function(req, res) {
    var file = req.query.file;
    var content = utils.readFile(file);
    res.send(content);
});

app.listen(3000);
