import streamlit as st
import requests
import json

st.set_page_config(page_title="BDD Generator UI", layout="wide")
st.title("BDD Generator")

if st.button("Suggest XPATH for Sample Element"):
    element = {"id": "username", "name": "user", "tag": "input"}
    resp = requests.post("http://localhost:8000/xpath/suggest", json=element)
    st.json(resp.json())

if st.button("Generate Random Value for Regex [A-Za-z]{5}\\d{3}"):
    resp = requests.post("http://localhost:8000/randomvalue", json={"regex": "[A-Za-z]{5}\\d{3}"})
    st.json(resp.json())

st.header("Encrypt/Decrypt Demo")
to_encrypt = st.text_input("Text to encrypt")
if st.button("Encrypt"):
    resp = requests.post("http://localhost:8000/encrypt", json={"value": to_encrypt})
    st.write("Encrypted:", resp.json().get("encrypted"))
enc = st.text_input("Paste encrypted string to decrypt")
if st.button("Decrypt"):
    resp = requests.post("http://localhost:8000/decrypt", json={"token": enc})
    st.write("Decrypted:", resp.json().get("decrypted"))

st.header("Generate Feature File Example")
if st.button("Generate Feature File (Sample)"):
    data_json = [
        {"element_name": "login_input", "action": "entered", "actual value": "DhinkiBagaPara@123", "Wait Type": "None"},
        {"element_name": "submit_button", "action": "clicked", "actual value": "", "Wait Type": "None"}
    ]
    object_repo_json = [
        {"object name": "login_input", "locator": "//*[@id='login']", "window number": 1, "framechain": ""},
        {"object name": "submit_button", "locator": "//*[@id='submit']", "window number": 1, "framechain": ""}
    ]
    resp = requests.post("http://localhost:8000/feature/generate", json={
        "data_json": data_json,
        "object_repo_json": object_repo_json,
        "feature_name": "Login Feature",
        "scenario_outline": "Test login with valid credentials"
    })
    st.code(resp.json().get("feature_file"), language="gherkin")
