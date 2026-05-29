/**
 * 场景 10: 综合混合 - 误报（Safe）测试
 * 这些样例不应被检出为漏洞
 */
var { exec } = require('child_process');
var express = require('express');
var app = express();

// 硬编码字符串 - 安全
app.get('/safe1', function(req, res) {
    exec('echo hello');
});

// 环境变量内部使用 - 安全（非用户可控）
app.get('/safe2', function(req, res) {
    var config = process.env.APP_CONFIG;
    if (config === 'debug') {
        console.log('debug mode');
    }
});

// 用户输入经过sanitize - 可能为误报
app.get('/safe3', function(req, res) {
    var input = req.query.id;
    if (/^[0-9]+$/.test(input)) {
        var cmd = 'cat /tmp/' + input;
        exec(cmd);
    }
});

// 使用常量映射
var ALLOWED_COMMANDS = {
    'status': 'systemctl status app',
    'restart': 'systemctl restart app'
};

app.get('/safe4', function(req, res) {
    var action = req.query.action;
    var cmd = ALLOWED_COMMANDS[action];
    if (cmd) {
        exec(cmd);
    }
});

// 输入仅用于 console.log - 安全
app.get('/safe5', function(req, res) {
    var name = req.query.name;
    console.log('User: ' + name);
    res.send('ok');
});

app.listen(3000);
