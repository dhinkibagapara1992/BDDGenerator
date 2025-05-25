import streamlit as st
import json
import os
from ai_executor import AIUIExecutor

st.set_page_config(page_title="AI UI Real-Time Operation Creator", layout="wide")
st.title("AI UI Operation Creator (Real-time)")

# --- Load AI config if exists ---
ai_config = {
    "model": "",
    "api_key": "",
    "api_base": ""
}
config_path = "ai_config_sonnet.json"
if os.path.exists(config_path):
    with open(config_path, "r") as f:
        try:
            loaded = json.load(f)
            ai_config.update(loaded)
        except Exception as e:
            st.warning(f"Could not read ai_config_sonnet.json: {e}")

with st.sidebar:
    st.header("AI Model Settings")
    model = st.text_input("Model Name", ai_config.get("model", "anthropic.claude-3-sonnet-20240229-v1:0"))
    api_key = st.text_input("API Key", ai_config.get("api_key", ""), type="password")
    api_base = st.text_input("API Base URL", ai_config.get("api_base", "https://your-bedrock-endpoint"))
    screenshot_dir = st.text_input("Screenshot Directory", "screenshots")
    report_path = st.text_input("Extent Report Path", "extent_report.html")
    st.markdown(
        """
        <small>
        Your API key and base URL are used only in your browser session and never sent anywhere else.
        </small>
        """, unsafe_allow_html=True
    )

st.markdown("""
### 📝 **Prompt Syntax Suggestions for Best Results**
- Prefer **step-by-step JSON** (see below) or clear, sequential natural language.
- **Example JSON:**
    ```json
    [
      {"eventType": "navigate", "locatorType": "url", "locator": "https://example.com"},
      {"eventType": "input", "locatorType": "label", "locator": "Username", "value": "myuser"},
      {"eventType": "input", "locatorType": "label", "locator": "Password", "value": "secret"},
      {"eventType": "click", "locatorType": "button_text", "locator": "Sign In"},
      {"eventType": "wait_js", "value": "return typeof window.myAppReady !== 'undefined' && window.myAppReady===true;"}
    ]
    ```
- Or natural language:
    - Go to https://example.com
    - Enter "myuser" in the Username field
    - Enter "secret" in the Password field
    - Click the "Sign In" button
    - Wait until the dashboard is fully loaded

**Tips:**  
- Use labels and visible text for fields and buttons.  
- Mention if a step requires waiting for a UI or JS state.  
- Specify frame or window if needed, else the system will try to auto-detect.
""")

if not api_key or not model or not api_base:
    st.warning("Please configure your AI API Key, Model, and Base URL in the sidebar, or set them in ai_config_sonnet.json.")
    st.stop()

ai_executor = AIUIExecutor(model, api_key, api_base, screenshot_dir=screenshot_dir, report_path=report_path)

prompt = st.text_area(
    "Describe your UI operation(s) to run on your browser (see syntax tips above):",
    "Go to https://example.com, enter \"myuser\" in the Username field, and click the Sign In button."
)

# State holders for results, cleaned for serialization
if 'object_repository' not in st.session_state:
    st.session_state['object_repository'] = {}
if 'actions' not in st.session_state:
    st.session_state['actions'] = []
if 'test_data' not in st.session_state:
    st.session_state['test_data'] = {}

def natural_language_for_step(step):
    et = step.get("eventType", "").lower()
    lt = step.get("locatorType", "")
    loc = step.get("locator", "")
    val = step.get("value", "")
    if et == "navigate":
        return f"Go to {loc}"
    if et == "input":
        label = loc
        if lt == "label":
            return f'Enter "{val}" in the {label} field'
        return f'Enter "{val}" in the field identified by {lt}: {label}'
    if et == "click":
        label = loc
        if lt in {"button_text", "link_text"}:
            return f'Click the "{label}" button'
        return f'Click the element identified by {lt}: {label}'
    if et == "press_enter":
        return f'Press ENTER on the element identified by {lt}: {loc}'
    if et == "wait":
        return f'Wait for {val} seconds'
    if et == "wait_js":
        return f'Wait until the JavaScript condition is true: {val}'
    return f"{et} on {lt}: {loc} {val}"

def add_to_object_repository(step):
    key = f"{step.get('locatorType')}:{step.get('locator')}"
    obj = {
        "locatorType": step.get("locatorType"),
        "locator": step.get("locator"),
        "framePath": step.get("framePath", []),
        "window": step.get("window", None)
    }
    st.session_state['object_repository'][key] = obj

def add_to_actions(step, nl_step):
    action = {
        "natural_language": nl_step,
        "step": {k: v for k, v in step.items() if k in ["eventType", "locatorType", "locator", "value", "framePath", "window"]}
    }
    st.session_state['actions'].append(action)

def add_to_test_data(step):
    if step.get("eventType") == "input":
        key = f"{step.get('locatorType')}:{step.get('locator')}"
        st.session_state['test_data'][key] = step.get("value")

def clean_dict_for_json(obj):
    # Recursively clean dicts/lists to eliminate unserializable entries
    if isinstance(obj, dict):
        return {k: clean_dict_for_json(v) for k, v in obj.items() if is_json_serializable(v)}
    elif isinstance(obj, list):
        return [clean_dict_for_json(x) for x in obj if is_json_serializable(x)]
    else:
        return obj

def is_json_serializable(value):
    try:
        json.dumps(value)
        return True
    except Exception:
        return False

if st.button("Execute UI Operation"):
    with st.spinner("Asking AI to plan steps..."):
        steps = ai_executor.ai_parse_steps(prompt)
    if not steps:
        st.error("AI could not generate a plan from your request. Try rephrasing.")
    else:
        st.success("AI plan ready! Executing in your browser...")
        logs = []
        step_results = ai_executor.run_steps(steps, log_callback=lambda msg: logs.append(msg))
        st.write("### Step Validation")
        for i, step in enumerate(steps):
            nl_step = natural_language_for_step(step)
            # Find status for this step
            step_logs = [log for log in ai_executor.extent_logs if f"Step {i+1}:" in log['message']]
            step_pass = any(log.get('status') == 'PASS' for log in step_logs)
            st.write(f"**Step {i+1}:** {nl_step}")
            if step_pass:
                val = st.checkbox(f"Mark as correct (validated)?", key=f"correct_{i}")
                if val:
                    add_to_object_repository(step)
                    add_to_actions(step, nl_step)
                    add_to_test_data(step)
            else:
                st.write(":warning: This step did not PASS in the automation logs.")
        st.write("----")
        st.write("**Execution Log:**")
        st.text("\n".join(logs))
        st.write(f"**Extent Report:** [{report_path}]({report_path})")

        # Download sections: object repository, actions, test data
        st.write("### Download Artifacts")
        col1, col2, col3 = st.columns(3)
        with col1:
            try:
                object_repo_clean = clean_dict_for_json(st.session_state['object_repository'])
                obj_repo_json = json.dumps(object_repo_clean, indent=2, ensure_ascii=False)
                st.download_button("Download Object Repository", obj_repo_json, file_name="object_repository.json")
            except Exception as e:
                st.error(f"Object repo not serializable: {e}")
        with col2:
            try:
                actions_clean = clean_dict_for_json(st.session_state['actions'])
                actions_json = json.dumps(actions_clean, indent=2, ensure_ascii=False)
                st.download_button("Download Actions", actions_json, file_name="actions.json")
            except Exception as e:
                st.error(f"Actions not serializable: {e}")
        with col3:
            try:
                test_data_clean = clean_dict_for_json(st.session_state['test_data'])
                test_data_json = json.dumps(test_data_clean, indent=2, ensure_ascii=False)
                st.download_button("Download Test Data", test_data_json, file_name="test_data.json")
            except Exception as e:
                st.error(f"Test data not serializable: {e}")
