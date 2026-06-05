<?php
/**
 * Source Discovery Benchmark - 用户自定义 source producer
 *
 * 场景：getInput() 是一个自定义函数，内部访问 $_GET，
 *       processInput() 调用 getInput()，最终传入 system()。
 * 预期：Source Discovery 识别 getInput() 为 source producer，
 *       system(getInput()) 被检出为命令注入。
 */

// 用户自定义 source producer — 内部访问 $_GET
function getInput($key) {
    return $_GET[$key];
}

// 中间处理层 — 调用 source producer
function processInput($cmd) {
    return escapeshellarg($cmd);
}

// sink — 调用中间层结果
$userInput = getInput("cmd");
$safeInput = processInput($userInput);
echo $safeInput;
