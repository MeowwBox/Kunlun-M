<?php
// ============ 类型验证函数测试 ============

// T1: is_numeric 阻断（不应报告SQL注入漏洞）
$id = $_GET['id'];
if (is_numeric($id)) {
    $query = "SELECT * FROM users WHERE id=" . $id;
    mysqli_query($conn, $query);
}

// T2: ctype_digit 阻断（不应报告XSS）
$name = $_GET['name'];
if (ctype_digit($name)) {
    echo "<div>" . $name . "</div>";
}

// T3: is_numeric 不阻断（else 分支，应报告漏洞）
$id2 = $_GET['id2'];
if (is_numeric($id2)) {
    // 安全分支
} else {
    $query2 = "SELECT * FROM users WHERE id=" . $id2;
    mysqli_query($conn, $query2);
}

// T4: preg_match 严格全匹配阻断（不应报告SQL注入）
$page = $_GET['page'];
if (preg_match('/^\d+$/', $page)) {
    $query3 = "SELECT * FROM articles WHERE page=" . $page;
    mysqli_query($conn, $query3);
}

// T5: preg_match 非严格匹配（应报告SQL注入）
$key = $_GET['key'];
if (preg_match('/\d/', $key)) {
    $query4 = "SELECT * FROM data WHERE `key`='" . $key . "'";
    mysqli_query($conn, $query4);
}

// T6: 无过滤（应报告SQL注入）
$raw = $_GET['raw'];
$query5 = "SELECT * FROM data WHERE id=" . $raw;
mysqli_query($conn, $query5);

// T7: ctype_alnum 阻断（不应报告XSS）
$user = $_GET['user'];
if (ctype_alnum($user)) {
    echo "Hello " . $user;
}

// T8: is_int 阻断（不应报告SQL注入）
$port = $_GET['port'];
if (is_int($port)) {
    $query6 = "SELECT * FROM services WHERE port=" . $port;
    mysqli_query($conn, $query6);
}

// T9: ctype_alpha 阻断（不应报告XSS）
$letter = $_GET['letter'];
if (ctype_alpha($letter)) {
    echo "<b>" . $letter . "</b>";
}

// T10: preg_match 宽松前缀匹配（应报告SQL注入，不阻断）
$cmd = $_GET['cmd'];
if (preg_match('/^ls/', $cmd)) {
    system($cmd);
}
