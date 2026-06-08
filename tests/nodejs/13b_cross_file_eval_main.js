/**
 * 场景 13b: 跨文件追踪 - 主文件通过 require 引入封装的 eval
 * 预期：CVI-3003 eval RCE（跨文件检测）
 */
var utils = require('./13a_cross_file_eval_utils');

var expr = process.argv[2];
var result = utils.evaluateExpression(expr);
console.log(result);
