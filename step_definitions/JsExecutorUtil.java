package utils;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
public class JsExecutorUtil {
    public static void waitForPageLoad(WebDriver driver) {
        new org.openqa.selenium.support.ui.WebDriverWait(driver, 30).until(
            webDriver -> ((JavascriptExecutor) webDriver).executeScript("return document.readyState").equals("complete"));
    }
}
