package utils;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.File;
import java.util.List;
import java.util.Map;
import java.util.HashMap;

public class ObjectRepositoryUtil {
    private static final String OBJ_REPO_JSON_PATH = "object_repository/object_repository.json";
    private static Map<String, String> locatorMap = null;

    private static void loadRepo() {
        if (locatorMap != null) return;
        locatorMap = new HashMap<>();
        try {
            ObjectMapper mapper = new ObjectMapper();
            List<Map<String, Object>> repoList = mapper.readValue(new File(OBJ_REPO_JSON_PATH), List.class);
            for (Map<String, Object> entry : repoList) {
                String name = (String) entry.get("object name");
                String locator = (String) entry.get("locator");
                if (name != null && locator != null) {
                    locatorMap.put(name, locator);
                }
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to read object_repository.json: " + e.getMessage(), e);
        }
    }

    public static String getLocator(String elementName) {
        loadRepo();
        return locatorMap.get(elementName);
    }
}
