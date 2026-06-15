<?php
// 多层间接调用测试
$cmd = $_GET['cmd'];
$func = 'system';      // 第一层：字符串赋值
$func2 = $func;         // 第二层：变量传递
$func2($cmd);           // 第三层：间接调用，应检出命令注入
