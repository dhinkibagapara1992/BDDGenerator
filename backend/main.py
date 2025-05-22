from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from ai_xpath import get_ai_xpath_suggestions
from selenium_manager import SeleniumSessionManager
from encryption import encrypt, decrypt
from feature_generator import generate_feature_file, generate_step_definitions, generate_java_helpers
from object_repo import ObjectRepositoryManager
from regex_random import generate_random_value

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

selenium_manager = SeleniumSessionManager()
obj_repo_manager = ObjectRepositoryManager()

@app.post("/xpath/suggest")
def xpath_suggest(element_data: dict = Body(...)):
    return {"suggestions": get_ai_xpath_suggestions(element_data)}

@app.post("/randomvalue")
def random_value(payload: dict = Body(...)):
    regex = payload.get("regex")
    return {"value": generate_random_value(regex)}

@app.post("/encrypt")
def encrypt_value(payload: dict = Body(...)):
    return {"encrypted": encrypt(payload.get("value", ""))}

@app.post("/decrypt")
def decrypt_value(payload: dict = Body(...)):
    return {"decrypted": decrypt(payload.get("token", ""))}

@app.post("/feature/generate")
def feature_generate(payload: dict = Body(...)):
    data_json = payload.get("data_json", [])
    object_repo_json = payload.get("object_repo_json", [])
    feature_name = payload.get("feature_name", "Sample Feature")
    scenario_outline = payload.get("scenario_outline", "")
    feature_str = generate_feature_file(data_json, object_repo_json, feature_name, scenario_outline)
    return {"feature_file": feature_str}

@app.post("/stepdefinitions/generate")
def stepdefs_generate(payload: dict = Body(...)):
    data_json = payload.get("data_json", [])
    object_repo_json = payload.get("object_repo_json", [])
    return {"step_definitions": generate_step_definitions(data_json, object_repo_json)}

@app.get("/javahelpers")
def java_helpers():
    return generate_java_helpers()
    
@app.post("/feature/write")
def feature_write(payload: dict = Body(...)):
    data_json = payload.get("data_json", [])
    object_repo_json = payload.get("object_repo_json", [])
    feature_name = payload.get("feature_name", "Sample Feature")
    scenario_outline = payload.get("scenario_outline", "")
    feature_str = generate_feature_file(data_json, object_repo_json, feature_name, scenario_outline)
    with open(f"../feature_files/{feature_name.lower().replace(' ', '_')}.feature", "w") as f:
        f.write(feature_str)
    return {"success": True}
