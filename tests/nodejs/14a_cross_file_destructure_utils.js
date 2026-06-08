/**
 * 场景 14a: 跨文件追踪 - 解构导入方式
 * utils 模块导出多个危险函数
 */
var child_process = require('child_process');

function executeCmd(cmd) {
    return child_process.exec(cmd);
}

function readContent(path) {
    return require('fs').readFileSync(path, 'utf-8');
}

module.exports = {
    executeCmd: executeCmd,
    readContent: readContent
};
