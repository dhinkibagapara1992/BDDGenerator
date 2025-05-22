package utils;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.File;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

public class DataUtil {
    private static final String DATA_JSON_PATH = "test_data/data.json";
    private static Map<String, String> dataMap = null;

    private static void loadData() {
        if (dataMap != null) return;
        dataMap = new HashMap<>();
        try {
            ObjectMapper mapper = new ObjectMapper();
            List<Map<String, Object>> dataList = mapper.readValue(new File(DATA_JSON_PATH), List.class);
            for (Map<String, Object> entry : dataList) {
                String name = (String) entry.get("element name");
                String value = (String) entry.get("actual value");
                if (name != null && value != null) {
                    dataMap.put(name, value);
                }
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to read data.json: " + e.getMessage(), e);
        }
    }

    public static String getValue(String key) {
        loadData();
        return dataMap.getOrDefault(key, "");
    }
}
