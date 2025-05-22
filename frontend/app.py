import streamlit as st
import requests
import time
import json

def get_unique_element_name(base, existing_names):
    if base not in existing_names:
        return base
    counter = 2
    while f"{base}_{counter}" in existing_names:
        counter += 1
    return f"{base}_{counter}"

def get_element_names():
    names = set()
    for action in st.session_state.actions:
        names.add(action.get("objectName", ""))
    for obj in st.session_state.object_repo:
        names.add(obj.get("objectName", ""))
    for td in st.session_state.test_data:
        names.add(td.get("objectName", ""))
    return names

def is_duplicate_element_name(name, idx, section):
    count = 0
    for i, action in enumerate(st.session_state.actions):
        if section == "actions" and i == idx:
            continue
        if action.get("objectName", "") == name:
            count += 1
    for i, obj in enumerate(st.session_state.object_repo):
        if section == "object_repo" and i == idx:
            continue
        if obj.get("objectName", "") == name:
            count += 1
    for i, td in enumerate(st.session_state.test_data):
        if section == "test_data" and i == idx:
            continue
        if td.get("objectName", "") == name:
            count += 1
    return count > 0

# ---- Streamlit Page Config (NO deploy button) ----
st.set_page_config(page_title="Enterprise BDD Generator", layout="wide", initial_sidebar_state="auto", menu_items={})

# ---- Session State ----
if "actions" not in st.session_state:
    st.session_state.actions = []
if "object_repo" not in st.session_state:
    st.session_state.object_repo = []
if "test_data" not in st.session_state:
    st.session_state.test_data = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "last_action_count" not in st.session_state:
    st.session_state.last_action_count = 0
if "polling_enabled" not in st.session_state:
    st.session_state.polling_enabled = False
if "stop_requested" not in st.session_state:
    st.session_state.stop_requested = False

API_URL = "http://localhost:8000"

# ---- Header and Controls ----
st.title("Enterprise BDD Generator")

colA, colB, colC, colD = st.columns([2,2,2,2])
with colA:
    url = st.text_input("Enter URL", placeholder="e.g. https://yourapp.com")
with colB:
    if st.button("Load URL"):
        resp = requests.post(f"{API_URL}/browser/launch", json={"url": url})
        st.session_state.session_id = resp.json()["session_id"]
        st.success("URL loaded in browser. Recording actions...")
        st.session_state.stop_requested = False
        st.session_state.polling_enabled = True
with colC:
    if st.button("Stop"):
        # Just stop polling, retain all actions/objects/data
        st.session_state.stop_requested = True
        st.session_state.polling_enabled = False
        st.info("Polling stopped. You can still view and edit recorded data.")
with colD:
    if st.button("Clear Session"):
        # Clear all session data
        st.session_state.actions = []
        st.session_state.object_repo = []
        st.session_state.test_data = []
        st.session_state.session_id = None
        st.session_state.last_action_count = 0
        st.session_state.polling_enabled = False
        st.session_state.stop_requested = False
        st.rerun()

def poll_for_actions():
    if not st.session_state.session_id:
        return 0
    resp = requests.get(
        f"{API_URL}/browser/actions",
        params={"session_id": st.session_state.session_id}
    )
    actions = resp.json().get("actions", [])
    new_count = 0
    element_names = get_element_names()
    for action in actions:
        already_exists = any(a.get("timestamp") == action.get("timestamp") and a.get("eventType") == action.get("eventType")
                             for a in st.session_state.actions if "timestamp" in a and "eventType" in a)
        if already_exists:
            continue
        if action.get("type") == "pageload":
            st.session_state.actions.append({
                "objectName": f"pageload_{len(st.session_state.actions)+1}",
                "eventType": "pageload",
                "actualValue": action.get("url", ""),
                "timestamp": action.get("timestamp", ""),
                "windowTitle": action.get("title", ""),
                "frameChain": "",
                "locator": "",
                "locatorType": "",
                "locatorSuggestions": [],
                "elementType": "",
                "targetElement": "",
                "suggestedName": "",
                "chosenXpath": "",
            })
        else:
            object_name = action.get("objectName") or f"{action.get('elementType','element')}_{action.get('suggestedName','')}"
            object_name = get_unique_element_name(object_name, element_names)
            element_names.add(object_name)
            st.session_state.actions.append({
                "objectName": object_name,
                "eventType": action.get("eventType", ""),
                "actualValue": action.get("actualValue", ""),
                "timestamp": action.get("timestamp", ""),
                "windowTitle": action.get("windowTitle", ""),
                "frameChain": action.get("frameChain", ""),
                "locator": action.get("locator", ""),
                "locatorType": action.get("locatorType", ""),
                "locatorSuggestions": action.get("locatorSuggestions", []),
                "elementType": action.get("elementType", ""),
                "targetElement": action.get("targetElement", ""),
                "suggestedName": action.get("suggestedName", ""),
                "chosenXpath": action.get("locator", ""),
            })
            st.session_state.object_repo.append({
                "objectName": object_name,
                "locator": action.get("locator", ""),
                "locatorType": action.get("locatorType", ""),
                "locatorSuggestions": action.get("locatorSuggestions", []),
                "frameChain": action.get("frameChain", ""),
                "windowTitle": action.get("windowTitle", ""),
                "elementType": action.get("elementType", ""),
                "targetElement": action.get("targetElement", ""),
                "suggestedName": action.get("suggestedName", ""),
                "chosenXpath": action.get("locator", ""),
            })
            if action.get("eventType") in ["input", "change", "blur", "enter"]:
                st.session_state.test_data.append({
                    "objectName": object_name,
                    "actualValue": action.get("actualValue", ""),
                    "expectedValue": "",
                    "eventType": action.get("eventType", ""),
                })
        new_count += 1
    return new_count

# ---- Real-time polling loop (runs only if enabled and not stopped) ----
if st.session_state.session_id and st.session_state.polling_enabled and not st.session_state.stop_requested:
    st.info(f"Session ID: {st.session_state.session_id}")
    fetch_placeholder = st.empty()
    for _ in range(1000):
        new_count = poll_for_actions()
        if new_count:
            fetch_placeholder.success(f"Added {new_count} new actions.")
        else:
            fetch_placeholder.info("Listening for browser actions...")
        time.sleep(0.1)
        st.rerun()

st.header("Recorded Actions")
if st.button("Add Action"):
    element_names = get_element_names()
    base_elem_name = "user_action"
    object_name = get_unique_element_name(base_elem_name, element_names)
    st.session_state.actions.append({
        "objectName": object_name,
        "eventType": "",
        "actualValue": "",
        "timestamp": "",
        "windowTitle": "",
        "frameChain": "",
        "locator": "",
        "locatorType": "",
        "locatorSuggestions": [],
        "elementType": "",
        "targetElement": "",
        "suggestedName": "",
        "chosenXpath": "",
    })

st.subheader("Actions List")
for idx, action in enumerate(st.session_state.actions):
    with st.expander(f"Action #{idx+1} - {action['objectName']}"):
        col1, col2, col3, col4 = st.columns([2,2,2,2])
        object_name = col1.text_input("Object Name", value=action["objectName"], key=f"aname_{idx}", placeholder="e.g. textbox_username")
        duplicate = is_duplicate_element_name(object_name, idx, "actions")
        if duplicate:
            col1.error("Duplicate object name! Please update to a unique name.")
        action["objectName"] = object_name
        action["eventType"] = col2.text_input("Event Type", value=action.get("eventType", ""), key=f"aevent_{idx}", placeholder="e.g. click, input")
        action["actualValue"] = col3.text_input("Actual Value", value=action.get("actualValue", ""), key=f"aval_{idx}", placeholder="e.g. value entered/clicked")
        action["timestamp"] = col4.text_input("Timestamp", value=action.get("timestamp", ""), key=f"atime_{idx}", placeholder="Auto-filled")
        st.text_input("Window Title", value=action.get("windowTitle", ""), key=f"awindow_{idx}", disabled=True, placeholder="Auto-filled")
        st.text_input("Frame Chain", value=action.get("frameChain", ""), key=f"aframe_{idx}", disabled=True, placeholder="Auto-filled")
        # Object type dropdown
        element_type_options = ["textbox", "button", "dropdown", "link", "textarea", "checkbox", "radio", "password", "other"]
        xpath_entered = action.get("chosenXpath", "") and action["chosenXpath"] != "No locator found"
        action["elementType"] = st.selectbox(
            "Object Type", element_type_options, 
            index=element_type_options.index(action.get("elementType", "textbox")) if action.get("elementType", "textbox") in element_type_options else 0,
            key=f"aetype_{idx}", disabled=not xpath_entered
        )
        st.text_input("Suggested Name", value=action.get("suggestedName", ""), key=f"asname_{idx}", disabled=True, placeholder="Auto-generated")
        st.text_area("Target HTML Element", value=action.get("targetElement", ""), key=f"atargetel_{idx}", disabled=True, placeholder="Auto-captured")
        # Dropdown for best xpath suggestion, with manual override
        locator_options = [l['locator'] for l in action.get("locatorSuggestions", [])] if action.get("locatorSuggestions") else [action.get("locator", "")]
        if not locator_options or locator_options == [""]:
            locator_options = ["No locator found"]
        if "chosenXpath" not in action or not action["chosenXpath"]:
            action["chosenXpath"] = locator_options[0]
        action["chosenXpath"] = st.selectbox(
            "Best XPath (Dropdown)", locator_options,
            index=locator_options.index(action["chosenXpath"]) if action["chosenXpath"] in locator_options else 0,
            key=f"axpath_{idx}", disabled=False
        )
        action["chosenXpath"] = st.text_input(
            "Update XPath (edit below if needed):", value=action["chosenXpath"], key=f"axpathedit_{idx}",
            placeholder="Paste or select a valid XPath here"
        )
        st.text_input("Locator Type", value=action.get("locatorType", ""), key=f"alocatype_{idx}", disabled=not xpath_entered, placeholder="Auto-filled")
        if action.get("locatorSuggestions"):
            st.text("All Locator Suggestions:")
            for locidx, loc in enumerate(action["locatorSuggestions"]):
                st.code(f"{loc.get('locatorType','')}: {loc.get('locator','')}")
        if st.button("❌ Delete", key=f"delaction_{idx}"):
            st.session_state.actions.pop(idx)
            st.rerun()

st.header("Object Repository")
if st.button("Add Object Repo Entry"):
    element_names = get_element_names()
    base_elem_name = "object"
    object_name = get_unique_element_name(base_elem_name, element_names)
    st.session_state.object_repo.append({
        "objectName": object_name,
        "locator": "",
        "locatorType": "",
        "locatorSuggestions": [],
        "frameChain": "",
        "windowTitle": "",
        "elementType": "",
        "targetElement": "",
        "suggestedName": "",
        "chosenXpath": "",
    })

for idx, obj in enumerate(st.session_state.object_repo):
    with st.expander(f"Object #{idx+1} - {obj['objectName']}"):
        col1, col2, col3, col4 = st.columns([2,2,2,1])
        object_name = col1.text_input(
            "Object Name", value=obj["objectName"], key=f"or_ename_{idx}",
            placeholder="e.g. textbox_username"
        )
        duplicate = is_duplicate_element_name(object_name, idx, "object_repo")
        if duplicate:
            col1.error("Duplicate object name! Please update to a unique name.")
        obj["objectName"] = object_name
        locator_options = [l['locator'] for l in obj.get("locatorSuggestions", [])] if obj.get("locatorSuggestions") else [obj.get("locator", "")]
        if not locator_options or locator_options == [""]:
            locator_options = ["No locator found"]
        if "chosenXpath" not in obj or not obj["chosenXpath"]:
            obj["chosenXpath"] = locator_options[0]
        obj["chosenXpath"] = st.selectbox(
            "Best XPath (Dropdown)", locator_options,
            index=locator_options.index(obj["chosenXpath"]) if obj["chosenXpath"] in locator_options else 0,
            key=f"or_xpath_{idx}", disabled=False
        )
        obj["chosenXpath"] = st.text_input(
            "Update XPath (edit below if needed):", value=obj["chosenXpath"],
            key=f"or_xpathedit_{idx}", placeholder="Paste or select a valid XPath here"
        )
        xpath_entered = obj["chosenXpath"] and obj["chosenXpath"] != "No locator found"
        element_type_options = ["textbox", "button", "dropdown", "link", "textarea", "checkbox", "radio", "password", "other"]
        obj["elementType"] = col2.selectbox(
            "Object Type", element_type_options,
            index=element_type_options.index(obj.get("elementType", "textbox")) if obj.get("elementType", "textbox") in element_type_options else 0,
            key=f"or_elemtype_{idx}", disabled=not xpath_entered
        )
        obj["locatorType"] = col3.text_input("Locator Type", value=obj.get("locatorType", ""), key=f"or_ltype_{idx}", disabled=not xpath_entered, placeholder="Auto-filled")
        if col4.button("❌ Delete", key=f"or_del_{idx}"):
            st.session_state.object_repo.pop(idx)
            st.rerun()
        st.text_area(
            "Locator Suggestions",
            value="\n".join([f"{l['locatorType']}: {l['locator']}" for l in obj.get("locatorSuggestions",[])]),
            key=f"or_locsugg_{idx}", disabled=True
        )
        st.text_input("Frame Chain", value=obj.get("frameChain", ""), key=f"or_frame_{idx}", disabled=not xpath_entered, placeholder="Auto-filled")
        st.text_input("Window Title", value=obj.get("windowTitle", ""), key=f"or_window_{idx}", disabled=not xpath_entered, placeholder="Auto-filled")
        st.text_input("Suggested Name", value=obj.get("suggestedName", ""), key=f"or_sname_{idx}", disabled=True, placeholder="Auto-generated")
        st.text_area("Target HTML Element", value=obj.get("targetElement", ""), key=f"or_html_{idx}", disabled=True, placeholder="Auto-captured")

st.write("Object Repository JSON:", st.session_state.object_repo)

st.header("Test Data")
if st.button("Add Test Data Entry"):
    element_names = get_element_names()
    base_elem_name = "testdata"
    object_name = get_unique_element_name(base_elem_name, element_names)
    st.session_state.test_data.append({
        "objectName": object_name,
        "actualValue": "",
        "expectedValue": "",
        "eventType": "",
    })

for idx, td in enumerate(st.session_state.test_data):
    with st.expander(f"TestData #{idx+1} - {td['objectName']}"):
        col1, col2, col3, col4 = st.columns([2,2,2,1])
        object_name = col1.text_input("Object Name", value=td["objectName"], key=f"td_ename_{idx}", placeholder="e.g. textbox_username")
        duplicate = is_duplicate_element_name(object_name, idx, "test_data")
        if duplicate:
            col1.error("Duplicate object name! Please update to a unique name.")
        td["objectName"] = object_name
        td["actualValue"] = col2.text_input("Actual Value", value=td.get("actualValue",""), key=f"td_aval_{idx}", placeholder="e.g. user input")
        td["expectedValue"] = col3.text_input("Expected Value", value=td.get("expectedValue",""), key=f"td_eval_{idx}", placeholder="e.g. expected assertion value")
        td["eventType"] = col4.text_input("Event Type", value=td.get("eventType",""), key=f"td_event_{idx}", placeholder="e.g. input")
        if col4.button("❌ Delete", key=f"td_del_{idx}"):
            st.session_state.test_data.pop(idx)
            st.rerun()

st.write("Test Data JSON:", st.session_state.test_data)

st.header("Auto-generate All Files (Java BDD Framework)")
feature_name = st.text_input("Feature Name", value="MyFeature", placeholder="e.g. Login Feature")
scenario_outline = st.text_area("Scenario Outline (optional)", placeholder="Describe the scenario here.")

if st.button("Generate Files"):
    payload = {
        "actions": st.session_state.actions,
        "object_repo": st.session_state.object_repo,
        "test_data": st.session_state.test_data,
        "feature_name": feature_name,
        "scenario_outline": scenario_outline
    }
    resp = requests.post(f"{API_URL}/generate/all", json=payload)
    if resp.ok:
        result = resp.json()
        st.success("Files generated successfully!")
        st.download_button("Download Feature File", data=result["feature_file"], file_name=f"{feature_name.replace(' ', '_').lower()}.feature")
        st.download_button("Download Step Definitions (Java)", data=result["step_definitions"], file_name=f"{feature_name.replace(' ', '_').lower()}_Steps.java")
        st.download_button("Download Cucumber Runner (Java)", data=result["runner"], file_name=f"{feature_name.replace(' ', '_').lower()}_Runner.java")
        st.download_button("Download Actions JSON", data=json.dumps(result["actions_json"], indent=2), file_name="actions.json")
        st.download_button("Download Object Repo JSON", data=json.dumps(result["object_repo_json"], indent=2), file_name="object_repo.json")
        st.download_button("Download Test Data JSON", data=json.dumps(result["test_data_json"], indent=2), file_name="test_data.json")
    else:
        st.error("Generation failed!")
