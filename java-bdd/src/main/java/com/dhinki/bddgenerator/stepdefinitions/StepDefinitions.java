package com.dhinki.bddgenerator.stepdefinitions;

import io.cucumber.java.en.When;
import com.dhinki.bddgenerator.utils.ObjectRepositoryUtil;
import com.dhinki.bddgenerator.utils.DataUtil;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

public class StepDefinitions {
    private WebDriver driver; // Should be managed by your test framework

    @When("^I perform the action \"([^\"]*)\" on element \"([^\"]*)\" with value \"([^\"]*)\"$")
    public void performActionWithValue(String action, String element, String value) throws Exception {
        WebElement el = ObjectRepositoryUtil.findElement(driver, element);
        switch (action.toLowerCase()) {
            case "entered":
                el.clear();
                el.sendKeys(DataUtil.getValue(value));
                break;
            case "clicked":
                el.click();
                break;
            // Add more action handlers as needed
        }
    }

    @When("^I perform the action \"([^\"]*)\" on element \"([^\"]*)\"$")
    public void performAction(String action, String element) throws Exception {
        performActionWithValue(action, element, "");
    }
}
