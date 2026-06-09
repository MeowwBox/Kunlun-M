import javax.servlet.http.*;
import java.io.*;

public class PathServlet extends HttpServlet {
    private static final long serialVersionUID = 1L;
    private String basePath = "/var/data";

    public void init() {
        System.out.println("PathServlet initialized");
    }

    public void doGet(HttpServletRequest request) throws Exception {
        String file = request.getParameter("file");
        FileUtils.readConfig(file);
    }

    public void doPost(HttpServletRequest request) throws Exception {
        String path = request.getParameter("path");
        FileUtils.writeFile(path, "test content");
    }

    public void destroy() {
        System.out.println("PathServlet destroyed");
    }
}
