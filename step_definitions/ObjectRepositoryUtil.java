package utils;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import java.util.Map;
import java.util.HashMap;

public class ObjectRepositoryUtil {
    private static Map<String, String> repo = new HashMap<>();

    static {
        // Populate from JSON or config
        repo.put("login_input", "//*[@id='login']");
        repo.put("submit_button", "//*[@id='submit']");
    }

    public static WebElement findElement(WebDriver driver, String elementName) {
        String xpath = repo.get(elementName);
        if (xpath == null) throw new RuntimeException("Element not found in repo");
        return driver.findElement(By.xpath(xpath));
    }
}
