import java.sql.*;

public class SqlUtils {
    public static void queryUser(Connection conn, String username) throws SQLException {
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE name = '" + username + "'");
    }

    public static void queryUserById(Connection conn, String id) throws SQLException {
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery("SELECT * FROM users WHERE id = " + id);
    }

    public static void queryAll(Connection conn, String table) throws SQLException {
        Statement stmt = conn.createStatement();
        ResultSet rs = stmt.executeQuery("SELECT * FROM " + table);
    }
}
