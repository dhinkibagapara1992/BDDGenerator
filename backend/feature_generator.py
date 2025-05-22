from encryption import encrypt
import re

def escape_gherkin(val):
    # Escape | for Gherkin tables
    return val.replace('|', '\\|')

def generate_feature_file(data_json, object_repo_json, feature_name, scenario_outline):
    steps = []
    for a in data_json:
        step = f'    When I perform the action "{a["action"]}" on element "{a["element_name"]}"'
        if a.get("actual value"):
            step += f' with value "{escape_gherkin(a["actual value"])}"'
        if a.get("Wait Type") and a["Wait Type"] != "None":
            step += f' and wait until "{a["Wait Type"]}'
            if a["Wait Type"] == "Static":
                step += f' ({a["durationOfWait"]}s)'
            elif a["Wait Type"] in ["Dynamic (ExpectedCondition)", "Fluent Wait"]:
                step += f' ({a["ExpectedCondition"]})'
            step += '"'
        steps.append(step)

    gherkin = f"""Feature: {feature_name}
  {scenario_outline}

  Scenario Outline: {feature_name} scenario
    Given the test is initialized
"""
    for s in steps:
        gherkin += f"{s}\n"
    gherkin += "\n    Then the result should be verified\n\n    Examples:\n"
    gherkin += "      | actiontype | elementname | value | wait |\n"
    for a in data_json:
        val = escape_gherkin(a.get("actual value", ""))
        gherkin += f'      | {a["action"]} | {a["element_name"]} | {val} | {a.get("Wait Type","")} |\n'
    return gherkin

def generate_step_definitions(data_json, object_repo_json):
    # Java step definitions template
    return '''package step_definitions;

import io.cucumber.java.en.When;
import utils.ObjectRepositoryUtil;
import utils.DataUtil;
import utils.JsExecutorUtil;

public class StepDefinitions {
    @When("^I perform the action \\"([^\\"]*)\\" on element \\"([^\\"]*)\\" with value \\"([^\\"]*)\\"$")
    public void performActionWithValue(String action, String element, String value) throws Exception {
        // Implement action using ObjectRepositoryUtil and DataUtil
    }
    @When("^I perform the action \\"([^\\"]*)\\" on element \\"([^\\"]*)\\"$")
    public void performAction(String action, String element) throws Exception {
        // Implement action using ObjectRepositoryUtil
    }
}
'''

def generate_java_helpers():
    # ObjectRepositoryUtil, DataUtil, JsExecutorUtil stubs
    return {
        "ObjectRepositoryUtil.java": '''
package utils;
import java.util.Map;
public class ObjectRepositoryUtil {
    public static Map<String, String> getLocator(String elementName) {
        // Implement lookup
        return null;
    }
}
''',
        "DataUtil.java": '''
package utils;
public class DataUtil {
    public static String getValue(String key) {
        // Implement lookup
        return "";
    }
}
''',
        "JsExecutorUtil.java": '''
package utils;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
public class JsExecutorUtil {
    public static void waitForPageLoad(WebDriver driver) {
        new org.openqa.selenium.support.ui.WebDriverWait(driver, 30).until(
            webDriver -> ((JavascriptExecutor) webDriver).executeScript("return document.readyState").equals("complete"));
    }
}
'''
    }
