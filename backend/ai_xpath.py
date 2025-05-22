# import os
# import openai

# OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

# def get_ai_xpath_suggestions(element_data):
#     prompt = f"""
# Given this HTML element info:
# {element_data}

# Suggest 3 robust, production-grade XPATH locators for this element. Only return a Python list of strings.
# """

#     try:
#         openai.api_key = OPENAI_API_KEY
#         response = openai.ChatCompletion.create(
#             model="gpt-4",
#             messages=[{"role": "user", "content": prompt}],
#             temperature=0.3,
#             max_tokens=200
#         )
#         text = response["choices"][0]["message"]["content"]
#         xs = eval(text, {"__builtins__": {}})
#         assert isinstance(xs, list)
#         return xs
#     except Exception as e:
#         suggestions = []
#         if 'id' in element_data and element_data['id']:
#             suggestions.append(f"//*[@id='{element_data['id']}']")
#         if 'name' in element_data and element_data['name']:
#             suggestions.append(f"//*[@name='{element_data['name']}']")
#         if 'class' in element_data and element_data['class']:
#             suggestions.append(f"//*[@class='{element_data['class']}']")
#         if not suggestions:
#             suggestions.append(f"//{element_data.get('tag', 'div')}")
#         return suggestions

def get_ai_xpath_suggestions(element_data):
    """
    Returns robust XPATH suggestions using advanced heuristics (no AI/API calls).
    """
    tag = element_data.get("tag", "div")
    _id = element_data.get("id", "")
    _name = element_data.get("name", "")
    _class = element_data.get("class", "")
    _text = element_data.get("text", "")

    suggestions = []

    # 1. By ID
    if _id:
        suggestions.append(f"//*[@id='{_id}']")
    # 2. By name
    if _name:
        suggestions.append(f"//{tag}[@name='{_name}']")
    # 3. By class (supports multiple classes)
    if _class:
        classes = _class.split()
        for c in classes:
            suggestions.append(f"//{tag}[contains(concat(' ', normalize-space(@class), ' '), ' {c} ')]")
    # 4. By text
    if _text:
        suggestions.append(f"//{tag}[normalize-space(text())='{_text}']")
        suggestions.append(f"//{tag}[contains(text(), '{_text[:10]}')]")
    # 5. Combination of attributes
    attrs = []
    if _id:
        attrs.append(f"@id='{_id}'")
    if _name:
        attrs.append(f"@name='{_name}'")
    if _class:
        attrs.append(f"contains(concat(' ', normalize-space(@class), ' '), ' {_class.split()[0]} ')")
    if attrs:
        suggestions.append(f"//{tag}[" + " and ".join(attrs) + "]")
    # 6. Fallback: nth-of-type
    if element_data.get("index") is not None:
        suggestions.append(f"(//{tag})[{element_data['index']+1}]")
    # 7. Generic fallback
    suggestions.append(f"//{tag}")

    # Deduplicate
    return list(dict.fromkeys(suggestions))


def suggest_element_name(element_data, previous_label=None):
    """
    Suggests a human-readable element name from attributes or context (heuristics only).
    """
    _id = element_data.get("id", "")
    _name = element_data.get("name", "")
    _text = element_data.get("text", "")
    _placeholder = element_data.get("placeholder", "")
    tag = element_data.get("tag", "element")

    # Prefer ID
    if _id and not _id.startswith("ctl"):
        return _id.lower()
    # Then name
    if _name:
        return _name.lower()
    # Then text
    if _text:
        cleaned = _text.strip().replace(" ", "_").replace("\n", "").lower()
        if cleaned:
            return f"{tag}_{cleaned[:20]}"
    # Then placeholder
    if _placeholder:
        cleaned = _placeholder.strip().replace(" ", "_").lower()
        return f"{tag}_{cleaned[:20]}"
    # Then previous label
    if previous_label:
        cleaned = previous_label.strip().replace(" ", "_").lower()
        return f"{tag}_{cleaned[:20]}"
    # Fallback
    return f"{tag}_auto"
