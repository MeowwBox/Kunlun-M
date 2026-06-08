<?php
/**
 * 场景: PHP NewFunction - 封装函数内 eval，参数是函数形参
 * 预期: 生成 NewFunction 信号 (code=4)
 */
function evaluateExpression($expr) {
    return eval($expr);
}

function runScript($code) {
    eval($code);
}
