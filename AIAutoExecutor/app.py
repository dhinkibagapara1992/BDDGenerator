import streamlit as st
import json
import os
from ai_executor import AIUIExecutor
from datetime import datetime

st.set_page_config(page_title="AI UI Real-Time Operation Creator", layout="wide")
st.title("AI UI Operation Creator (Real-time)")

# Load AI config if exists
ai_config = {"model": "", "api_key": "", "api_base": ""}
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
    st.markdown("""
        <small>Your API key and base URL are used only in your browser session and never sent anywhere else.</small>
    """, unsafe_allow_html=True)

if not api_key or not model or not api_base:
    st.warning("Please configure your AI API Key, Model, and Base URL in the sidebar or ai_config_sonnet.json.")
    st.stop()

ai_executor = AIUIExecutor(model, api_key, api_base, screenshot_dir=screenshot_dir, report_path=report_path)

prompt = st.text_area(
    "Describe your UI operation(s) to run on your browser:",
    "Go to https://example.com, enter \"myuser\" in the Username field, and click the Sign In button."
)

# Session state for test data
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
        return f'Enter "{val}" in the {lt}: {loc} field'
    if et == "click":
        return f'Click on the {lt}: {loc} element'
    if et == "hover":
        return f'Hover over the {lt}: {loc} element'
    if et == "drag_and_drop":
        target = step.get("targetLocator", "unknown")
        return f'Drag {lt}: {loc} and drop to {target}'
    if et == "press_enter":
        return f'Press ENTER on the {lt}: {loc} element'
    if et == "wait":
        return f'Wait for {val} seconds'
    if et == "wait_js":
        return f'Wait for JS condition: {val} to become true'
    if et == "switch_frame":
        return f'Switch to frame {loc}'
    if et == "switch_window":
        return f'Switch to window {loc}'
    return f"{et} on {lt}: {loc} with {val}"

def add_to_object_repository(step):
    key = f"{step.get('locatorType')}:{step.get('locator')}"
    st.session_state['object_repository'][key] = {
        "locatorType": step.get("locatorType"),
        "locator": step.get("locator"),
        "framePath": step.get("framePath", []),
        "window": step.get("window", None)
    }

def add_to_actions(step, nl):
    st.session_state['actions'].append({
        "natural_language": nl,
        "step": {k: v for k, v in step.items() if k in ["eventType", "locatorType", "locator", "value", "framePath", "window", "targetLocator"]}
    })

def add_to_test_data(step):
    if step.get("eventType") == "input":
        key = f"{step.get('locatorType')}:{step.get('locator')}"
        st.session_state['test_data'][key] = step.get("value")

def clean_dict_for_json(obj):
    if isinstance(obj, dict):
        return {k: clean_dict_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_dict_for_json(x) for x in obj]
    return obj

def generate_extent_report(logs, report_path):
    html = """
    <html><head><title>Extent Report</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .log { margin-bottom: 10px; padding: 10px; border-radius: 5px; }
        .PASS { background-color: #d4edda; }
        .FAIL { background-color: #f8d7da; }
        .INFO { background-color: #d1ecf1; }
        .log img { max-width: 400px; display: block; margin-top: 5px; border: 2px solid orange; }
        .timestamp { font-size: 0.8em; color: #555; }
    </style></head><body>
    <h1>Extent Report</h1>
    """
    for log in logs:
        status = log.get("status", "INFO")
        message = log.get("message", "")
        ts = log.get("timestamp", "")
        screenshot = log.get("screenshot_base64", None)
        html += f'<div class="log {status}">'
        html += f'<div><b>Status:</b> {status} <span class="timestamp">{ts}</span></div>'
        html += f'<div>{message}</div>'
        if screenshot:
            html += f'<img src="data:image/png;base64,{screenshot}" alt="Screenshot"/>'
        html += '</div>'
    html += "</body></html>"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

if st.button("Execute UI Operation"):
    with st.spinner("Asking AI to plan steps..."):
        steps = ai_executor.ai_parse_steps(prompt)
    if not steps:
        st.error("AI could not generate a plan from your request. Try rephrasing.")
    else:
        st.success("AI plan ready! Executing in your browser...")
        logs = []
        result = ai_executor.run_steps(steps, log_callback=lambda m: logs.append(m))

        st.write("### Step Validation")
        for i, step in enumerate(steps):
            nl_step = natural_language_for_step(step)
            step_logs = [log for log in logs if f"Step {i+1}:" in log.get('message', '')]
            step_pass = any(log.get('status') == 'PASS' for log in step_logs)
            st.write(f"**Step {i+1}:** {nl_step}")
            if step_pass:
                if st.checkbox(f"Mark Step {i+1} as Correct (Validated)?", key=f"correct_{i}"):
                    add_to_object_repository(step)
                    add_to_actions(step, nl_step)
                    add_to_test_data(step)
            else:
                st.warning(f"Step {i+1} did not PASS in automation logs.")

        st.write("----")
        st.write("**Execution Log:**")
        st.text("\n".join([log.get('message','') for log in logs]))

        generate_extent_report(logs, report_path)
        st.markdown(f"**Extent Report:** [{report_path}]({report_path})")

        st.write("### Download Artifacts")
        col1, col2, col3 = st.columns(3)
        with col1:
            try:
                obj_repo_json = json.dumps(clean_dict_for_json(st.session_state['object_repository']), indent=2)
                st.download_button("Download Object Repository", obj_repo_json, file_name="object_repository.json")
            except Exception as e:
                st.error(f"Object repo error: {e}")
        with col2:
            try:
                actions_json = json.dumps(clean_dict_for_json(st.session_state['actions']), indent=2)
                st.download_button("Download Actions", actions_json, file_name="actions.json")
            except Exception as e:
                st.error(f"Actions error: {e}")
        with col3:
            try:
                test_data_json = json.dumps(clean_dict_for_json(st.session_state['test_data']), indent=2)
                st.download_button("Download Test Data", test_data_json, file_name="test_data.json")
            except Exception as e:
                st.error(f"Test data error: {e}")
