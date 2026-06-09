import java.io.*;

public class FileUtils {
    public static void readConfig(String filePath) throws Exception {
        FileInputStream fis = new FileInputStream(filePath);
    }

    public static void writeFile(String filePath, String content) throws Exception {
        FileOutputStream fos = new FileOutputStream(filePath);
        fos.write(content.getBytes());
        fos.close();
    }

    public static void readFile(String filePath) throws Exception {
        BufferedReader br = new BufferedReader(new FileReader(filePath));
        String line = br.readLine();
        while (line != null) {
            System.out.println(line);
            line = br.readLine();
        }
    }
}
