/**
 * 场景 7: async/await 模式
 * 现代 Node.js 异步模式
 * 预期：如果引擎能理解 async/await 语义则检出
 */
var { exec } = require('child_process');
var fs = require('fs');
var express = require('express');
var app = express();

function promisifyExec(cmd) {
    return new Promise(function(resolve, reject) {
        exec(cmd, function(err, stdout) {
            if (err) reject(err);
            else resolve(stdout);
        });
    });
}

// async 路由回调
app.get('/async1', async function(req, res) {
    var cmd = req.query.cmd;
    var result = await promisifyExec(cmd);
    res.send(result);
});

// async 函数内部调用
async function handleRequest(input) {
    var output = await promisifyExec(input);
    return output;
}

app.get('/async2', async function(req, res) {
    var result = await handleRequest(req.query.cmd);
    res.send(result);
});

// async await + try-catch
app.get('/async3', async function(req, res) {
    try {
        var cmd = req.query.exec;
        var stdout = await promisifyExec(cmd);
        res.send(stdout);
    } catch (e) {
        res.status(500).send(e.message);
    }
});

app.listen(3000);
