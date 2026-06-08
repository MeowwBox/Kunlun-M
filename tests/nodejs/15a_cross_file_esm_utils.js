/**
 * 场景 15a: 跨文件追踪 - ESM import 语法
 * utils 模块使用 ES module 语法导出
 */
var child_process = require('child_process');

export function spawnProcess(cmd) {
    return child_process.exec(cmd, function(err, stdout) {
        return stdout;
    });
}

export default function runCmd(cmd) {
    return child_process.execSync(cmd);
}
