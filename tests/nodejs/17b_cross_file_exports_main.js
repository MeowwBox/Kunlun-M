/**
 * 场景 17b: 跨文件追踪 - exports.xxx 赋值 + require().xxx 属性访问
 * 预期：跨文件检测到 processInput 内部的 eval sink
 */
var utils = require('./17a_cross_file_exports_utils');

var data = process.argv[2];
utils.processInput(data);
