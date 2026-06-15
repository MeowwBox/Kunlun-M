// 多层间接调用测试
const userInput = process.argv[2];
const func = eval;        // 第一层：赋值
const func2 = func;        // 第二层：传递
func2(userInput);          // 第三层：间接调用，应检出
