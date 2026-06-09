<?php
/**
 * Case 30: PHP 间接调用 - 变量函数调用
 * $func = 'system'; $func($cmd)
 * 预期: 检出 CVI-1011 (命令执行)
 */

$func = 'system';

if (isset($_GET['cmd'])) {
    $cmd = $_GET['cmd'];
    // 间接调用: $func 是变量, 实际执行 system($cmd)
    $func($cmd);
}
