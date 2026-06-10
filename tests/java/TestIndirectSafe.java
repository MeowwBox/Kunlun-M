/**
 * Case 31: Java 间接调用 - 安全场景（不应检出）
 * 通过方法引用赋值，但参数是硬编码的
 */

import java.util.function.Function;

public class TestIndirectSafe {
    public static void main(String[] args) throws Exception {
        Runtime rt = Runtime.getRuntime();

        // 间接调用模式，但参数是硬编码字符串，不存在注入风险
        Function<String, Process> execFunc = rt::exec;
        Process p = execFunc.apply("ls -la");
    }
}
