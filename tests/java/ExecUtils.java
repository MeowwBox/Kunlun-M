public class ExecUtils {
    public static void executeCommand(String cmd) throws Exception {
        Runtime.getRuntime().exec(cmd);
    }

    public static void executeCommandWithEnv(String cmd, String[] env) throws Exception {
        Runtime.getRuntime().exec(cmd, env);
    }

    public static void executeCommandInDir(String cmd, String[] env, java.io.File dir) throws Exception {
        Runtime.getRuntime().exec(cmd, env, dir);
    }
}
