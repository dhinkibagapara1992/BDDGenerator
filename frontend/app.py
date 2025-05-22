import streamlit as st
import requests
import json

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Enterprise BDD Generator", layout="wide")
st.title("Enterprise BDD Generator")

# --- Session State ---
if "actions" not in st.session_state:
    st.session_state.actions = []
if "object_repo" not in st.session_state:
    st.session_state.object_repo = []

# --- Actions Table ---
st.header("Test Actions")
if st.button("Add Action"):
    st.session_state.actions.append({
        "element_name": "",
        "action": "",
        "actual value": "",
        "Wait Type": "None",
        "durationOfWait": 0,
        "ExpectedCondition": "",
        "Pooling Every": 0.5,
        "random": False,
        "regex": ""
    })

for idx, action in enumerate(st.session_state.actions):
    col1, col2, col3, col4, col5 = st.columns([2,2,2,2,1])
    action["element_name"] = col1.text_input("Element Name", value=action["element_name"], key=f"ename_{idx}")
    action["action"] = col2.selectbox("Action", ["clicked", "entered", "selected"], key=f"action_{idx}")
    action["actual value"] = col3.text_input("Value", value=action["actual value"], key=f"aval_{idx}")
    action["random"] = col4.checkbox("Random?", value=action["random"], key=f"rand_{idx}")
    if action["random"]:
        action["regex"] = st.text_input("Regex for random", value=action.get("regex", ""), key=f"regex_{idx}")
        if st.button("Generate Random", key=f"genrand_{idx}"):
            resp = requests.post(f"{API_URL}/randomvalue", json={"regex": action["regex"]})
            action["actual value"] = resp.json().get("value", "")
            st.experimental_rerun()
    if col5.button("❌", key=f"del_{idx}"):
        st.session_state.actions.pop(idx)
        st.experimental_rerun()

    # Wait types
    wait_types = ["None", "Static", "Dynamic (ExpectedCondition)", "Fluent Wait"]
    action["Wait Type"] = st.selectbox("Wait Type", wait_types, key=f"wtype_{idx}", index=wait_types.index(action.get("Wait Type", "None")))
    if action["Wait Type"] == "Static":
        action["durationOfWait"] = st.number_input("Static Wait (s)", min_value=0, max_value=60, value=int(action.get("durationOfWait",0)), key=f"wait_{idx}")
    elif action["Wait Type"] in ["Dynamic (ExpectedCondition)", "Fluent Wait"]:
        action["ExpectedCondition"] = st.text_input("Expected Condition", value=action.get("ExpectedCondition",""), key=f"ec_{idx}")
        if action["Wait Type"] == "Fluent Wait":
            action["Pooling Every"] = st.number_input("Pooling Every (s)", min_value=0.1, max_value=10.0, value=float(action.get("Pooling Every",0.5)), key=f"pool_{idx}")

# --- Object Repository Table ---
st.header("Object Repository")
if st.button("Add Object Repo Row"):
    st.session_state.object_repo.append({
        "object name": "",
        "locator": "",
        "window number": 1,
        "framechain": "",
        "element type": "",
        "targetElement": "",
        "suggested locators": []
    })

for idx, obj in enumerate(st.session_state.object_repo):
    ocol1, ocol2, ocol3, ocol4, ocol5, ocol6 = st.columns([2,2,1,2,2,1])
    obj["object name"] = ocol1.text_input("Object Name", value=obj["object name"], key=f"oname_{idx}")
    obj["locator"] = ocol2.text_input("Locator", value=obj["locator"], key=f"loc_{idx}")
    obj["window number"] = ocol3.number_input("Window #", min_value=1, max_value=10, value=int(obj.get("window number", 1)), key=f"winnum_{idx}")
    obj["framechain"] = ocol4.text_input("Frame Chain", value=obj["framechain"], key=f"frame_{idx}")
    obj["element type"] = ocol5.selectbox("Element Type", ["textBox", "link", "button", "dropDownList", "SearcheableDropDown", "Datepicker", "textArea", "RadioButton", "Label", "Mouse", "Scroll", "Window", "Checkbox", "Image"], key=f"etype_{idx}")
    obj["targetElement"] = ocol5.text_input("Target Element", value=obj["targetElement"], key=f"targ_{idx}")
    if ocol6.button("❌", key=f"odel_{idx}"):
        st.session_state.object_repo.pop(idx)
        st.experimental_rerun()

    if st.button("AI XPATH Suggest", key=f"aix_{idx}"):
        element_info = {"id": obj["object name"], "tag": obj["element type"], "name": obj["object name"]}
        resp = requests.post(f"{API_URL}/xpath/suggest", json=element_info)
        obj["suggested locators"] = resp.json().get("suggestions", [])
        st.success("AI XPATHs: " + str(obj["suggested locators"]))

# --- Download JSONs ---
st.header("Export Data")
if st.button("Download Data JSON"):
    st.download_button("Download data.json", json.dumps(st.session_state.actions, indent=2), "data.json", mime="application/json")
if st.button("Download Object Repo JSON"):
    st.download_button("Download object_repository.json", json.dumps(st.session_state.object_repo, indent=2), "object_repository.json", mime="application/json")

# --- Feature and Step Definition Generation ---
st.header("Feature & Step Definitions")
feature_name = st.text_input("Feature Name")
scenario_outline = st.text_area("Scenario Outline/Description")

if st.button("Generate Feature File"):
    resp = requests.post(f"{API_URL}/feature/generate", json={
        "data_json": st.session_state.actions,
        "object_repo_json": st.session_state.object_repo,
        "feature_name": feature_name,
        "scenario_outline": scenario_outline
    })
    st.code(resp.json().get("feature_file",""), language="gherkin")

if st.button("Generate Step Definitions"):
    resp = requests.post(f"{API_URL}/stepdefinitions/generate", json={
        "data_json": st.session_state.actions,
        "object_repo_json": st.session_state.object_repo
    })
    st.code(resp.json().get("step_definitions",""), language="java")
