package com.dhinki.bddgenerator.utils;

import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.WebDriverWait;

public class JsExecutorUtil {
    public static void waitForPageLoad(WebDriver driver) {
        new WebDriverWait(driver, java.time.Duration.ofSeconds(30)).until(
            webDriver -> ((JavascriptExecutor) webDriver).executeScript("return document.readyState").equals("complete"));
    }
}
