<?php
/**
 * Source Discovery Benchmark - 用户自定义 source producer (版本2)
 *
 * 场景：safeHelper() 访问硬编码安全值，不应被标记为 source producer。
 *       getInput() 访问 $_POST，应被标记为 source producer。
 *       只有通过 getInput() 的数据路径才应被检出。
 */

// 安全函数 — 不访问任何 source
function safeHelper() {
    return "hello";
}

// 用户自定义 source producer — 访问 $_POST
function getUserData($key) {
    return $_POST[$key];
}

// 混合使用 — safeHelper 不应检出，getUserData 应检出
$safe = safeHelper();
$user = getUserData("name");
echo $safe;   // line 21 — 不应检出
echo $user;   // line 22 — 应检出
