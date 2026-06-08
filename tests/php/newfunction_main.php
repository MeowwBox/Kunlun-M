<?php
/**
 * 场景: PHP NewFunction - 主文件 require 引入封装函数，参数来自用户输入
 * 预期: NewCore 二次扫描后检出 CVI-1004 (eval)
 */
require_once './newfunction_utils.php';

if (isset($_GET['expr'])) {
    $expr = $_GET['expr'];
    $result = evaluateExpression($expr);
    echo $result;
}
