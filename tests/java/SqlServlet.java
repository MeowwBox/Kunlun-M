import javax.servlet.http.*;
import java.sql.*;

public class SqlServlet extends HttpServlet {
    private static final long serialVersionUID = 1L;
    private Connection conn;

    public void init() throws Exception {
        Class.forName("com.mysql.jdbc.Driver");
        conn = DriverManager.getConnection("jdbc:mysql://localhost:3306/test");
    }

    public void doGet(HttpServletRequest request) throws Exception {
        String user = request.getParameter("user");
        SqlUtils.queryUser(conn, user);
    }

    public void doPost(HttpServletRequest request) throws Exception {
        String id = request.getParameter("id");
        SqlUtils.queryUserById(conn, id);
    }

    public void destroy() {
        try { if (conn != null) conn.close(); } catch (Exception e) {}
    }
}
