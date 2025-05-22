from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from selenium_manager import SeleniumSessionManager

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)
selenium_manager = SeleniumSessionManager()

GENERATED_FILES_DIR = "./generated"
os.makedirs(GENERATED_FILES_DIR, exist_ok=True)

@app.post("/browser/launch")
def launch_browser(payload: dict = Body(...)):
    url = payload.get("url")
    session_id = payload.get("session_id")
    if not session_id:
        from uuid import uuid4
        session_id = str(uuid4())
    selenium_manager.launch_browser(url, session_id)
    return {"session_id": session_id}

@app.post("/browser/inject_recorder")
def inject_recorder(payload: dict = Body(...)):
    session_id = payload.get("session_id")
    return {"success": selenium_manager.inject_recorder(session_id)}

@app.get("/browser/actions")
def get_actions(session_id: str):
    return selenium_manager.get_actions(session_id)

@app.post("/browser/clear_actions")
def clear_actions(session_id: str = Body(...)):
    return selenium_manager.clear_actions(session_id)

@app.get("/browser/driver_status")
def driver_status(session_id: str):
    driver = selenium_manager.get_driver(session_id)
    try:
        if driver:
            driver.title  # Try accessing to check if still alive
            return {"status": "alive"}
    except Exception:
        pass
    return {"status": "dead"}

@app.post("/generate/all")
def generate_all(payload: dict = Body(...)):
    """
    Expects payload to contain:
      - actions: []
      - object_repo: []
      - test_data: []
      - feature_name: str
      - scenario_outline: str
    """
    actions = payload.get("actions", [])
    object_repo = payload.get("object_repo", [])
    test_data = payload.get("test_data", [])
    feature_name = payload.get("feature_name", "Sample Feature")
    scenario_outline = payload.get("scenario_outline", "")

    # Write JSON files
    with open(f"{GENERATED_FILES_DIR}/actions.json", "w") as f:
        json.dump(actions, f, indent=2)
    with open(f"{GENERATED_FILES_DIR}/object_repo.json", "w") as f:
        json.dump(object_repo, f, indent=2)
    with open(f"{GENERATED_FILES_DIR}/test_data.json", "w") as f:
        json.dump(test_data, f, indent=2)

    # Generate feature file
    feature_file = generate_feature_file(actions, object_repo, feature_name, scenario_outline)
    with open(f"{GENERATED_FILES_DIR}/{feature_name.replace(' ', '_').lower()}.feature", "w") as f:
        f.write(feature_file)

    # Generate step definitions (Java)
    step_defs = generate_java_step_definitions(feature_name, actions, object_repo, test_data)
    with open(f"{GENERATED_FILES_DIR}/{feature_name.replace(' ', '_').lower()}_Steps.java", "w") as f:
        f.write(step_defs)

    # Generate Cucumber runner (Java)
    runner_code = generate_java_cucumber_runner(feature_name)
    with open(f"{GENERATED_FILES_DIR}/{feature_name.replace(' ', '_').lower()}_Runner.java", "w") as f:
        f.write(runner_code)

    return {
        "status": "success",
        "feature_file": feature_file,
        "step_definitions": step_defs,
        "runner": runner_code,
        "actions_json": actions,
        "object_repo_json": object_repo,
        "test_data_json": test_data
    }

def generate_feature_file(actions, object_repo, feature_name, scenario_outline):
    steps = []
    for action in actions:
        if action.get("eventType") == "pageload":
            steps.append(f'Given the page is loaded: "{action.get("actualValue","")}"')
        elif action.get("eventType") == "click":
            steps.append(f'When the user clicks on "{action.get("objectName","")}"')
        elif action.get("eventType") in ["input", "change", "blur", "enter"]:
            steps.append(f'And the user enters "{action.get("actualValue","")}" into "{action.get("objectName","")}"')
        elif action.get("eventType") == "keepalive":
            steps.append(f"And session keepalive popup is handled automatically")
    scenario = f'''Scenario: {scenario_outline or feature_name}
    ''' + "\n    ".join(steps)
    return f'''Feature: {feature_name}

  {scenario}
'''

def generate_java_step_definitions(feature_name, actions, object_repo, test_data):
    obj_map = {o['objectName']: o for o in object_repo}
    imports = (
        "import io.cucumber.java.en.*;\n"
        "import org.openqa.selenium.*;\n"
        "import org.openqa.selenium.chrome.ChromeDriver;\n"
        "import java.util.*;\n"
        "import util.KeepaliveHandler;\n"
    )
    class_def = f"public class {feature_name.replace(' ', '')}Steps "+"{\n"
    setup_vars = (
        "    private WebDriver driver;\n"
        "    private KeepaliveHandler keepaliveHandler;\n"
        "    private Map<String, Map<String, Object>> objectRepo;\n"
        "    private Map<String, Object> testData;\n"
    )
    before = (
        "    @Before\n"
        "    public void setUp() throws Exception {\n"
        "        driver = new ChromeDriver();\n"
        "        keepaliveHandler = new KeepaliveHandler(driver);\n"
        "        keepaliveHandler.start();\n"
        "        objectRepo = DataHelper.loadObjectRepo(\"generated/object_repo.json\");\n"
        "        testData = DataHelper.loadTestData(\"generated/test_data.json\");\n"
        "    }\n"
    )
    after = (
        "    @After\n"
        "    public void tearDown() {\n"
        "        if (keepaliveHandler != null) keepaliveHandler.stop();\n"
        "        if (driver != null) driver.quit();\n"
        "    }\n"
    )
    step_lines = []
    seen_steps = set()
    for action in actions:
        obj = obj_map.get(action.get("objectName"), {})
        if action.get("eventType") == "pageload" and "pageload" not in seen_steps:
            step_lines.append(
                '    @Given("the page is loaded: {url}")\n'
                '    public void page_loaded(String url) {\n'
                '        driver.get(url);\n'
                '    }\n'
            )
            seen_steps.add("pageload")
        elif action.get("eventType") == "click" and "click" not in seen_steps:
            step_lines.append(
                '    @When("the user clicks on {object}")\n'
                '    public void user_clicks_on(String object) {\n'
                '        String xpath = (String)objectRepo.get(object).get("chosenXpath");\n'
                '        driver.findElement(By.xpath(xpath)).click();\n'
                '    }\n'
            )
            seen_steps.add("click")
        elif action.get("eventType") in ["input", "change", "blur", "enter"] and "input" not in seen_steps:
            step_lines.append(
                '    @And("the user enters {value} into {object}")\n'
                '    public void user_enters(String value, String object) {\n'
                '        String xpath = (String)objectRepo.get(object).get("chosenXpath");\n'
                '        driver.findElement(By.xpath(xpath)).sendKeys(value);\n'
                '    }\n'
            )
            seen_steps.add("input")
        elif action.get("eventType") == "keepalive" and "keepalive" not in seen_steps:
            step_lines.append(
                '    @And("session keepalive popup is handled automatically")\n'
                '    public void session_keepalive_handled() { /* handled by KeepaliveHandler */ }\n'
            )
            seen_steps.add("keepalive")
    class_end = "}\n"
    data_helper = """
class DataHelper {
    public static Map<String, Map<String, Object>> loadObjectRepo(String path) {
        try {
            String json = new String(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(path)));
            org.json.JSONArray arr = new org.json.JSONArray(json);
            Map<String, Map<String, Object>> map = new HashMap<>();
            for (int i = 0; i < arr.length(); i++) {
                org.json.JSONObject o = arr.getJSONObject(i);
                Map<String, Object> entry = new HashMap<>();
                for(String k : o.keySet()) entry.put(k, o.get(k));
                map.put(o.getString("objectName"), entry);
            }
            return map;
        } catch (Exception e) { throw new RuntimeException(e); }
    }
    public static Map<String, Object> loadTestData(String path) {
        try {
            String json = new String(java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(path)));
            org.json.JSONArray arr = new org.json.JSONArray(json);
            Map<String, Object> map = new HashMap<>();
            for (int i = 0; i < arr.length(); i++) {
                org.json.JSONObject o = arr.getJSONObject(i);
                map.put(o.getString("objectName"), o.get("actualValue"));
            }
            return map;
        } catch (Exception e) { throw new RuntimeException(e); }
    }
}
"""
    return imports + class_def + setup_vars + before + after + "".join(step_lines) + class_end + data_helper

def generate_java_cucumber_runner(feature_name):
    name = feature_name.replace(' ', '_').lower()
    class_name = feature_name.replace(' ', '') + "Runner"
    return f"""import org.junit.runner.RunWith;
import io.cucumber.junit.Cucumber;
import io.cucumber.junit.CucumberOptions;

@RunWith(Cucumber.class)
@CucumberOptions(
    features = "generated/{name}.feature",
    glue = {{"."}},
    plugin = {{"pretty", "html:target/cucumber-reports.html"}}
)
public class {class_name} {{}}
"""
