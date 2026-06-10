/**
 * Case 30: Java 间接调用 - 方法引用赋值后调用（应该检出）
 * 将 Runtime.exec 通过方法引用赋值给变量，再通过变量调用
 * 预期: 检出 CVI-6003 (命令注入)
 */

import java.util.function.Function;

public class TestIndirectExec {
    public static void main(String[] args) throws Exception {
        String cmd = args[0];
        Runtime rt = Runtime.getRuntime();

        // 间接调用模式：通过方法引用将 sink 赋值给变量
        Function<String, Process> execFunc = rt::exec;
        Process p = execFunc.apply(cmd);
    }
}
