import os
import openai

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")

def get_ai_xpath_suggestions(element_data):
    """
    Uses OpenAI GPT-4 API to suggest robust XPATHs for a given HTML element.
    """
    prompt = f"""
Given this HTML element info:
{element_data}

Suggest 3 robust, production-grade XPATH locators for this element. Only return a Python list of strings.
"""

    try:
        openai.api_key = OPENAI_API_KEY
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200
        )
        # Extract the list from the response
        text = response["choices"][0]["message"]["content"]
        # Safely extract list from text
        xs = eval(text, {"__builtins__": {}})
        assert isinstance(xs, list)
        return xs
    except Exception as e:
        # fallback to basic heuristics
        suggestions = []
        if 'id' in element_data and element_data['id']:
            suggestions.append(f"//*[@id='{element_data['id']}']")
        if 'name' in element_data and element_data['name']:
            suggestions.append(f"//*[@name='{element_data['name']}']")
        if 'class' in element_data and element_data['class']:
            suggestions.append(f"//*[@class='{element_data['class']}']")
        if not suggestions:
            suggestions.append(f"//{element_data.get('tag', 'div')}")
        return suggestions
