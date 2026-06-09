<?php
/**
 * Case 32: PHP 间接调用 - 安全场景 (硬编码参数)
 * $func = 'system'; $func('ls -la')
 * 预期: 不应检出 (参数是硬编码字符串)
 */

$func = 'system';

// 参数是硬编码字符串，不是用户输入
$func('ls -la');
