package step_definitions;

import io.cucumber.java.en.When;
import utils.ObjectRepositoryUtil;
import utils.DataUtil;
import utils.JsExecutorUtil;

public class StepDefinitions {
    @When("^I perform the action \"([^\"]*)\" on element \"([^\"]*)\" with value \"([^\"]*)\"$")
    public void performActionWithValue(String action, String element, String value) throws Exception {
        // Implement action using ObjectRepositoryUtil and DataUtil
    }
    @When("^I perform the action \"([^\"]*)\" on element \"([^\"]*)\"$")
    public void performAction(String action, String element) throws Exception {
        // Implement action using ObjectRepositoryUtil
    }
}
