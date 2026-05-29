/**
 * 场景 1: 多函数调用链
 * 污点传播：req.query.cmd → handleInput() → processCmd() → exec()
 * 预期：CVI-3100 命令注入 检出
 */
const { exec } = require('child_process');
const express = require('express');
const app = express();

// 二次包装：用户输入 → 中间函数 → 危险函数
function processCmd(cmd) {
    exec(cmd, function(err, stdout) {
        console.log(stdout);
    });
}

function handleInput(input) {
    var cmd = input.trim();
    processCmd(cmd);
}

app.get('/run1', function(req, res) {
    var userInput = req.query.cmd;
    handleInput(userInput);
});

// 三层包装
function layer3(s) {
    exec(s);
}

function layer2(s) {
    layer3(s);
}

function layer1(s) {
    layer2(s);
}

app.get('/run2', function(req, res) {
    layer1(req.query.cmd);
});

app.listen(3000);
