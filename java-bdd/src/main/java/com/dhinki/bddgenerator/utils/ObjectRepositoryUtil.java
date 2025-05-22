package com.dhinki.bddgenerator.utils;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.openqa.selenium.*;
import java.io.InputStream;
import java.util.*;

public class ObjectRepositoryUtil {
    private static final String OBJ_REPO_JSON_PATH = "/object_repository.json";
    private static Map<String, Map<String, Object>> locatorMap = null;

    private static void loadRepo() {
        if (locatorMap != null) return;
        locatorMap = new HashMap<>();
        try (InputStream is = ObjectRepositoryUtil.class.getResourceAsStream(OBJ_REPO_JSON_PATH)) {
            ObjectMapper mapper = new ObjectMapper();
            List<Map<String, Object>> repoList = mapper.readValue(is, List.class);
            for (Map<String, Object> entry : repoList) {
                String name = (String) entry.get("object name");
                if (name != null) {
                    locatorMap.put(name, entry);
                }
            }
        } catch (Exception e) {
            throw new RuntimeException("Failed to read object_repository.json: " + e.getMessage(), e);
        }
    }

    public static String getLocator(String elementName) {
        loadRepo();
        Map<String, Object> obj = locatorMap.get(elementName);
        return obj == null ? null : (String) obj.get("locator");
    }

    public static int getWindowNumber(String elementName) {
        loadRepo();
        Map<String, Object> obj = locatorMap.get(elementName);
        if (obj == null) return 1;
        Object win = obj.get("window number");
        return win == null ? 1 : (win instanceof Integer ? (Integer)win : Integer.parseInt(win.toString()));
    }

    public static String getFrameChain(String elementName) {
        loadRepo();
        Map<String, Object> obj = locatorMap.get(elementName);
        return obj == null ? "" : (String) obj.getOrDefault("framechain", "");
    }

    public static WebElement findElement(WebDriver driver, String elementName) {
        String locator = getLocator(elementName);
        int windowNumber = getWindowNumber(elementName);
        String frameChain = getFrameChain(elementName);

        // Switch to correct window
        if (windowNumber > 1) {
            List<String> handles = new ArrayList<>(driver.getWindowHandles());
            if (windowNumber <= handles.size()) {
                driver.switchTo().window(handles.get(windowNumber - 1));
            } else {
                throw new NoSuchWindowException("Window number " + windowNumber + " not found");
            }
        }

        // Switch to nested frames if needed
        if (frameChain != null && !frameChain.isEmpty()) {
            String[] frames = frameChain.split("\\|\\|");
            for (String frame : frames) {
                frame = frame.trim();
                if (!frame.isEmpty()) {
                    driver.switchTo().frame(frame);
                }
            }
        }

        // Find element
        WebElement element = driver.findElement(By.xpath(locator));

        // After action is done, always return context to default
        driver.switchTo().defaultContent();

        return element;
    }
}
