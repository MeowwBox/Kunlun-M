/**
 * 场景 2a: 跨文件调用 - utils 模块
 * 导出封装了危险操作的函数
 */
var { exec } = require('child_process');
var fs = require('fs');

function runCommand(cmd) {
    return new Promise(function(resolve, reject) {
        exec(cmd, function(err, stdout, stderr) {
            if (err) reject(err);
            else resolve(stdout);
        });
    });
}

function readFile(path) {
    return fs.readFileSync(path, 'utf-8');
}

module.exports = {
    runCommand: runCommand,
    readFile: readFile
};
