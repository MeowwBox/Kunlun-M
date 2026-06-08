/**
 * 场景 14b: 跨文件追踪 - 解构导入 { executeCmd } from require
 * 预期：跨文件检测到 executeCmd 内部的 exec sink
 */
var { executeCmd } = require('./14a_cross_file_destructure_utils');

var cmd = process.argv[2];
executeCmd(cmd);
