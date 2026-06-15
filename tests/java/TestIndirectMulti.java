/**
 * Java 多层间接调用测试
 * execFunc = rt::exec; wrapper = execFunc; wrapper.apply(cmd)
 */

import java.util.function.Function;

public class TestIndirectMulti {
    public static void main(String[] args) throws Exception {
        String cmd = args[0];
        Runtime rt = Runtime.getRuntime();

        // 第一层：方法引用赋值
        Function<String, Process> execFunc = rt::exec;
        // 第二层：函数传递
        Function<String, Process> wrapper = execFunc;
        // 第三层：间接调用
        Process p = wrapper.apply(cmd);
    }
}
