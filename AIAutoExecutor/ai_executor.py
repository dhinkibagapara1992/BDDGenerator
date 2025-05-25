import openai
import time
import re
import json
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import (
    NoSuchElementException, NoSuchFrameException, StaleElementReferenceException,
    WebDriverException, TimeoutException
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class AIUIExecutor:
    def __init__(self, model, api_key, api_base, screenshot_dir='screenshots', report_path='extent_report.html'):
        self.client = openai.OpenAI(
            api_key=api_key,
            base_url=api_base
        )
        self.model = model
        self.screenshot_dir = screenshot_dir
        self.report_path = report_path
        self.extent_logs = []
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

    def ai_parse_steps(self, prompt):
        system_prompt = (
            "You are an expert UI automation agent. Given a user command describing UI operations, "
            "generate a JSON array of steps. Each step should have: "
            "eventType (click/input/navigate/press_enter/wait/wait_js), locatorType (url/xpath/css/id/name/label/button_text), "
            "locator (the selector or URL or label/button text), value (for input or wait), and optionally framePath (an array of frame-identifiers, xpath, css or name, "
            "if the element is inside one or more frames), and window (window handle or title if action is on a different window). "
            "For input operations, analyze the UI: find the LABEL or visible text (even if nested inside divs, tables, etc.), and produce an xpath that finds the input associated with that label, NOT just by id/name."
            "For click operations, use any clickable element (button, input[type=button|submit|image], link, role=button, or onclick handler)."
            "For wait_js, the value should be a JS expression to wait for (returns true when ready)."
            "If the element is inside a frame/iframe, provide the framePath as an array of locators needed to reach it."
            "Only output a JSON array. Do NOT explain or provide any text outside the JSON array."
            "Example:\n"
            "[{\"eventType\": \"navigate\", \"locatorType\": \"url\", \"locator\": \"https://example.com\"},"
            "{\"eventType\": \"input\", \"locatorType\": \"label\", \"locator\": \"Username\", \"value\": \"myuser\"},"
            "{\"eventType\": \"click\", \"locatorType\": \"button_text\", \"locator\": \"Sign In\"},"
            "{\"eventType\": \"wait_js\", \"value\": \"return typeof window.myAppReady !== 'undefined' && window.myAppReady===true;\"}]"
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        raw = None
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1200,
                temperature=0.2
            )
            raw = response.choices[0].message.content

            # Try to extract the first valid JSON array using regex
            match = re.search(r'(\[[\s\S]*?\])', raw)
            if match:
                json_str = match.group(1)
            else:
                # Fallback: try to find the first "[" and last "]" if not a pure array
                start = raw.find('[')
                end = raw.rfind(']')
                if start != -1 and end != -1:
                    json_str = raw[start:end+1]
                else:
                    raise ValueError("No JSON array found in AI response.")

            # Ensure special characters are escaped and JSON is valid
            steps = json.loads(json_str)
            return steps
        except Exception as e:
            print(f"AI error: {e}")
            if raw is not None:
                print("AI raw response:\n", raw)
            else:
                print("No AI raw response available (request failed before response was received).")
            return []

    def run_steps(self, steps, log_callback=None):
        driver = None
        logs = []
        self.extent_logs = []

        def log(msg, status="INFO", screenshot=None):
            logs.append(msg)
            self.extent_logs.append({
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": msg,
                "status": status,
                "screenshot": screenshot
            })
            if log_callback:
                log_callback(msg)

        def highlight_and_screenshot(elem, desc):
            try:
                original_style = driver.execute_script("var elem=arguments[0];return elem.getAttribute('style');", elem)
                driver.execute_script(
                    "arguments[0].setAttribute('data-original-style', arguments[1]);"
                    "arguments[0].style.border='3px solid red';"
                    "arguments[0].style.backgroundColor='yellow';", elem, original_style or "")
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                fname = f"{ts}_{re.sub(r'[^a-zA-Z0-9]', '_', desc)[:30]}.png"
                fpath = os.path.join(self.screenshot_dir, fname)
                driver.save_screenshot(fpath)
                # Restore style if still in DOM
                try:
                    if driver.execute_script("return arguments[0].isConnected;", elem):
                        driver.execute_script(
                            "arguments[0].setAttribute('style', arguments[0].getAttribute('data-original-style') or '');"
                            "arguments[0].removeAttribute('data-original-style');", elem)
                except Exception:
                    pass
                return fpath
            except Exception as e:
                log(f"Highlight/screenshot error: {e}", "INFO")
                return None

        def wait_for_js_ready(timeout=20, custom_ready_js=None):
            try:
                WebDriverWait(driver, timeout).until(
                    lambda d: d.execute_script("return document.readyState;") == "complete"
                )
                if custom_ready_js:
                    WebDriverWait(driver, timeout).until(
                        lambda d: d.execute_script(custom_ready_js)
                    )
            except TimeoutException:
                log(f"Timeout waiting for JS ready (custom: {custom_ready_js})", "FAIL")

        def switch_to_frame_path(frame_path):
            driver.switch_to.default_content()
            if not frame_path:
                return True
            for frame_locator in frame_path:
                frame_elem = self._find_elem(driver, 'xpath', frame_locator, log)
                if frame_elem:
                    try:
                        driver.switch_to.frame(frame_elem)
                    except NoSuchFrameException:
                        log(f"Frame not found: {frame_locator}", "FAIL")
                        return False
                else:
                    log(f"Frame element not found: {frame_locator}", "FAIL")
                    return False
            return True

        def auto_switch_to_frames(locator_type, locator):
            driver.switch_to.default_content()
            try:
                elem = self._find_elem(driver, locator_type, locator, log)
                if elem:
                    return elem
            except Exception:
                pass
            frames = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
            for idx, frame in enumerate(frames):
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                    elem = self._find_elem(driver, locator_type, locator, log)
                    if elem:
                        log(f"Auto switched to frame index {idx}", "INFO")
                        return elem
                    subframes = driver.find_elements(By.TAG_NAME, "iframe") + driver.find_elements(By.TAG_NAME, "frame")
                    for subidx, subframe in enumerate(subframes):
                        try:
                            driver.switch_to.frame(subframe)
                            elem = self._find_elem(driver, locator_type, locator, log)
                            if elem:
                                log(f"Auto switched to nested frame index {idx}->{subidx}", "INFO")
                                return elem
                        except Exception:
                            continue
                except Exception:
                    continue
            driver.switch_to.default_content()
            return None

        def wait_for_element(locator_type, locator, timeout=15):
            try:
                by_map = {
                    "xpath": By.XPATH,
                    "css": By.CSS_SELECTOR,
                    "id": By.ID,
                    "name": By.NAME
                }
                if locator_type in by_map:
                    return WebDriverWait(driver, timeout).until(
                        EC.visibility_of_element_located((by_map[locator_type], locator))
                    )
            except TimeoutException:
                log(f"Timeout waiting for element: {locator}", "FAIL")
                return None

        def switch_to_window(window_title_or_handle):
            try:
                if not window_title_or_handle:
                    return True
                if window_title_or_handle in driver.window_handles:
                    driver.switch_to.window(window_title_or_handle)
                    return True
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    if window_title_or_handle in driver.title:
                        return True
                log(f"Window '{window_title_or_handle}' not found.", "FAIL")
                return False
            except WebDriverException as e:
                log(f"Window switch error: {e}", "FAIL")
                return False

        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-extensions")
            options.add_argument("--start-maximized")
            driver = webdriver.Chrome(options=options)
            driver.implicitly_wait(7)
            for idx, step in enumerate(steps):
                event = step.get("eventType")
                locator_type = step.get("locatorType")
                locator = step.get("locator")
                value = step.get("value", "")
                frame_path = step.get("framePath", [])
                window_info = step.get("window", None)
                step_desc = f"{event}_{locator_type}_{locator}_{value}"
                log(f"Step {idx+1}: {event} | {locator_type} | {locator} | {value} | FramePath: {frame_path} | Window: {window_info}")

                try:
                    if window_info:
                        if not switch_to_window(window_info):
                            continue

                    if event == "navigate" and locator_type == "url":
                        driver.get(locator)
                        wait_for_js_ready()
                        log(f"Navigated to {locator}", "PASS", highlight_and_screenshot(driver.find_element(By.TAG_NAME, "body"), "navigate"))
                        continue

                    if event == "wait_js":
                        wait_for_js_ready(custom_ready_js=value)
                        log(f"Waited for JS: {value}", "PASS")
                        continue

                    if frame_path and not switch_to_frame_path(frame_path):
                        log(f"Failed to switch to frame path: {frame_path}", "FAIL", None)
                        continue
                    elif not frame_path:
                        driver.switch_to.default_content()

                    elem = None
                    if event in ["input", "click", "press_enter"]:
                        elem = wait_for_element(locator_type, locator)
                        if not elem:
                            elem = auto_switch_to_frames(locator_type, locator)

                    if event == "input":
                        if not elem:
                            alt_elem = self._find_elem_fallback(driver, locator_type, locator, log, input_mode=True)
                            if alt_elem:
                                elem = alt_elem
                                log(f"Recovered input element via fallback for locator: {locator}", "INFO")
                        if elem:
                            screenshot_path = highlight_and_screenshot(elem, step_desc)
                            elem.clear()
                            elem.send_keys(value)
                            log(f"Input '{value}' into {locator}", "PASS", screenshot_path)
                        else:
                            log(f"Failed to find element for input: {locator}", "FAIL", None)

                    elif event == "click":
                        clickable = elem
                        if not clickable:
                            clickable = self._find_elem_fallback(driver, locator_type, locator, log, input_mode=False)
                        if clickable:
                            screenshot_path = highlight_and_screenshot(clickable, step_desc)
                            try:
                                clickable.click()
                            except Exception:
                                try:
                                    driver.execute_script("arguments[0].click();", clickable)
                                except Exception as e:
                                    log(f"JS click failed: {e}", "FAIL", screenshot_path)
                            log(f"Clicked on {locator}", "PASS", screenshot_path)
                        else:
                            log(f"Failed to find clickable element: {locator}", "FAIL", None)

                    elif event == "press_enter":
                        if elem:
                            screenshot_path = highlight_and_screenshot(elem, step_desc)
                            elem.send_keys(Keys.ENTER)
                            log(f"Pressed ENTER on {locator}", "PASS", screenshot_path)
                        else:
                            log(f"Failed to find element to press ENTER: {locator}", "FAIL", None)

                    elif event == "wait":
                        duration = float(step.get("value", 1))
                        time.sleep(duration)
                        log(f"Waited for {duration} seconds", "PASS")
                    else:
                        log(f"Unknown event: {event}", "INFO")
                    time.sleep(1)
                except Exception as e:
                    log(f"Exception during step: {e}", "FAIL", None)
            self._generate_extent_report()
            return logs
        except Exception as e:
            log(f"Exception occurred: {e}", "FAIL")
        finally:
            if driver:
                driver.quit()

    def _find_elem(self, driver, locator_type, locator, log=None):
        try:
            by_map = {
                "xpath": By.XPATH,
                "css": By.CSS_SELECTOR,
                "id": By.ID,
                "name": By.NAME
            }
            if locator_type in by_map:
                return driver.find_element(by_map[locator_type], locator)
            elif locator_type == "label":
                return self._find_input_by_label(driver, locator, log)
            elif locator_type == "button_text":
                xpath = (
                    f"//button[normalize-space(text())='{locator}'] | "
                    f"//input[@type='button' and @value='{locator}'] | "
                    f"//input[@type='submit' and @value='{locator}'] | "
                    f"//a[normalize-space(text())='{locator}'] | "
                    f"//*[@role='button' and normalize-space(text())='{locator}']"
                )
                return driver.find_element(By.XPATH, xpath)
        except Exception:
            return None

    def _find_input_by_label(self, driver, label_text, log=None):
        try:
            label_text_lc = label_text.lower()
            labels = driver.find_elements(By.XPATH, f"//label[contains(translate(normalize-space(.), '{label_text_lc.upper()}', '{label_text_lc.lower()}'), '{label_text_lc}')]")
            for label in labels:
                for_attr = label.get_attribute('for')
                if for_attr:
                    input_elem = driver.find_element(By.ID, for_attr)
                    if input_elem:
                        return input_elem
                try:
                    input_elem = label.find_element(By.XPATH, ".//input")
                    if input_elem:
                        return input_elem
                except NoSuchElementException:
                    pass
                try:
                    input_elem = label.find_element(By.XPATH, "following::input[1]")
                    if input_elem:
                        return input_elem
                except NoSuchElementException:
                    pass
            input_elem = driver.find_element(By.XPATH, f"//*[contains(text(),'{label_text}')]/ancestor::*[self::div or self::td or self::th][1]/following::input[1]")
            if input_elem:
                return input_elem
        except Exception as e:
            if log:
                log(f"Label-input heuristic error: {e}", "INFO")
            return None

    def _find_elem_fallback(self, driver, locator_type, locator, log=None, input_mode=False):
        try:
            locator_lc = (locator or "").strip().lower()
            candidates = []
            tags = ["input", "button", "a", "textarea", "select", "*"] if not input_mode else ["input", "textarea", "select"]
            elements = []
            for tag in tags:
                try:
                    elements.extend(driver.find_elements(By.TAG_NAME, tag))
                except Exception:
                    continue
            for elem in elements:
                try:
                    if not elem.is_displayed() or not elem.is_enabled():
                        continue
                    text = (elem.text or "").strip().lower()
                    placeholder = (elem.get_attribute("placeholder") or "").lower()
                    aria_label = (elem.get_attribute("aria-label") or "").lower()
                    value = (elem.get_attribute("value") or "").lower()
                    label_for = ""
                    id_attr = elem.get_attribute("id") or ""
                    if id_attr:
                        labels = driver.find_elements(By.XPATH, f"//label[@for='{id_attr}']")
                        if labels:
                            label_for = labels[0].text.strip().lower()
                    score = 0
                    if locator_lc in [text, placeholder, aria_label, value, label_for]:
                        score = 3
                    elif any(locator_lc in s for s in [text, placeholder, aria_label, value, label_for]):
                        score = 2
                    elif input_mode and elem.tag_name.lower() in ["input", "textarea", "select"]:
                        score = 1
                    elif not input_mode:
                        score = 1
                    candidates.append((score, elem))
                except Exception:
                    continue
            candidates.sort(reverse=True, key=lambda x: x[0])
            for score, elem in candidates:
                if score > 0:
                    return elem
            return None
        except Exception as e:
            if log:
                log(f"Fallback element scan failed: {e}", "INFO")
            return None

    def _generate_extent_report(self):
        html = [
            '<html><head><title>Extent Report</title>',
            '<style>',
            'body{font-family:Arial;}',
            'table{border-collapse:collapse;width:100%;}',
            'th,td{border:1px solid #ddd;padding:8px;}',
            'tr:nth-child(even){background-color:#f2f2f2;}',
            'th{padding-top:12px;padding-bottom:12px;text-align:left;background-color:#4CAF50;color:white;}',
            '.PASS{color:green;} .FAIL{color:red;} .INFO{color:blue;}',
            '</style></head><body>',
            f'<h2>Extent Report - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</h2>',
            '<table><tr><th>Time</th><th>Status</th><th>Message</th><th>Screenshot</th></tr>'
        ]
        for entry in self.extent_logs:
            screenshot_html = f'<a href="{entry["screenshot"]}" target="_blank">View</a>' if entry["screenshot"] else ""
            html.append(
                f'<tr><td>{entry["time"]}</td>'
                f'<td class="{entry["status"]}">{entry["status"]}</td>'
                f'<td>{entry["message"]}</td>'
                f'<td>{screenshot_html}</td></tr>'
            )
        html.append('</table></body></html>')
        with open(self.report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(html))
