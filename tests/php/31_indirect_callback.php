<?php
/**
 * Case 31: PHP 间接调用 - call_user_func 回调
 * call_user_func('system', $cmd)
 * 预期: 检出 CVI-1011 (命令执行)
 */

if (isset($_GET['cmd'])) {
    $cmd = $_GET['cmd'];
    // call_user_func 回调: 第一个参数是字符串 'system'
    call_user_func('system', $cmd);
}
