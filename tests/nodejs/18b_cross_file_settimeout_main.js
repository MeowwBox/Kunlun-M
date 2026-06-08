/**
 * 场景 18b: 跨文件追踪 - setTimeout 封装调用
 * 预期：CVI-3003 setTimeout（跨文件检测）
 */
var utils = require('./18a_cross_file_settimeout_utils');

var code = process.argv[2];
utils.delayEval(code);
