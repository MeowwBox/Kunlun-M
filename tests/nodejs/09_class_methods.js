/**
 * 场景 9: ES6 Class 方法传播
 * 污点通过 class 的方法和属性传递
 * 预期：如果引擎能理解 class 结构则检出
 */
var { exec } = require('child_process');
var express = require('express');
var app = express();

class CommandExecutor {
    constructor() {
        this.cmd = '';
    }

    setCommand(input) {
        this.cmd = input;
    }

    run() {
        exec(this.cmd);
    }
}

class SafeExecutor {
    execute() {
        // 安全函数，不接收用户输入
        exec('echo safe');
    }
}

app.get('/class1', function(req, res) {
    var executor = new CommandExecutor();
    executor.setCommand(req.query.cmd);
    executor.run();
});

// 静态方法
class Utils {
    static processInput(data) {
        exec(data);
    }
}

app.get('/class2', function(req, res) {
    Utils.processInput(req.query.cmd);
});

// class 中通过方法链传递
class Handler {
    step1(input) {
        this.data = input;
        return this;
    }

    step2() {
        exec(this.data);
    }
}

app.get('/class3', function(req, res) {
    new Handler().step1(req.query.cmd).step2();
});

app.listen(3000);
