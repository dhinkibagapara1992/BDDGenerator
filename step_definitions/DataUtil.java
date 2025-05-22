package utils;
import java.util.Map;
import java.util.HashMap;

public class DataUtil {
    private static Map<String, String> data = new HashMap<>();

    static {
        // Populate from JSON or config
        data.put("login_input", "DhinkiBagaPara@123");
    }

    public static String getValue(String key) {
        return data.getOrDefault(key, "");
    }
}
