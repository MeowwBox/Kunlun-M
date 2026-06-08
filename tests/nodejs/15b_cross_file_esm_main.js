/**
 * 场景 15b: 跨文件追踪 - ESM import 导入
 * 预期：跨文件检测到 spawnProcess 内部的 exec sink
 */
import { spawnProcess } from './15a_cross_file_esm_utils.js';

app.get('/spawn', function(req, res) {
    var cmd = req.query.cmd;
    spawnProcess(cmd);
    res.send('done');
});
