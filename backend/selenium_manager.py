import threading
import time
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, WebDriverException

RECORDER_JS = """
(function(){
    // --- Helper Functions for XPath and Locators ---
    function isUniqueXPath(xpath) {
      try {
        let result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        return result.snapshotLength === 1;
      } catch {
        return false;
      }
    }

    function getAbsoluteXPath(el) {
      if (!el) return '';
      let segs = [];
      for (; el && el.nodeType === 1; el = el.parentNode) {
        if (el.hasAttribute('id')) {
          segs.unshift('//*[@id="' + el.getAttribute('id') + '"]');
          return segs.join('/');
        }
        let i = 1;
        for (let sib = el.previousSibling; sib; sib = sib.previousSibling) {
          if (sib.nodeType === 1 && sib.nodeName === el.nodeName) i++;
        }
        segs.unshift(el.nodeName.toLowerCase() + '[' + i + ']');
      }
      return '/' + segs.join('/');
    }

    function getAdvancedXPath(el) {
      if (!el || el.nodeType !== 1) return "";
      const tag = el.tagName.toLowerCase();
      if (el.id && isUniqueXPath(`//*[@id="${el.id}"]`)) return `//*[@id="${el.id}"]`;
      if (el.name && isUniqueXPath(`//${tag}[@name="${el.name}"]`)) return `//${tag}[@name="${el.name}"]`;
      for (const attr of Array.from(el.attributes)) {
        if (attr.name.startsWith('data-') && attr.value) {
          const xpath = `//${tag}[contains(@${attr.name}, "${attr.value}")]`;
          if (isUniqueXPath(xpath)) return xpath;
        }
      }
      for (const attr of ["aria-label", "placeholder", "title"]) {
        const val = el.getAttribute(attr);
        if (val && isUniqueXPath(`//${tag}[normalize-space(@${attr})="${val.trim()}"]`)) {
          return `//${tag}[normalize-space(@${attr})="${val.trim()}"]`;
        }
      }
      if (el.classList && el.classList.length) {
        for (const className of el.classList) {
          const xpath1 = `//${tag}[contains(concat(' ',normalize-space(@class),' '),' ${className} ')]`;
          if (isUniqueXPath(xpath1)) return xpath1;
          const xpath2 = `//${tag}[ancestor::*[contains(@class, "${className}")]]`;
          if (isUniqueXPath(xpath2)) return xpath2;
        }
      }
      const text = (el.textContent || '').trim();
      if (text && text.length < 50) {
        const textXpath1 = `//${tag}[normalize-space(text())="${text}"]`;
        if (isUniqueXPath(textXpath1)) return textXpath1;
        const textXpath2 = `//${tag}[contains(normalize-space(text()), "${text.split(" ")[0]}")]`;
        if (isUniqueXPath(textXpath2)) return textXpath2;
        const fsXpath = `//${tag}[following-sibling::*[normalize-space(text())="${text}"]]`;
        if (isUniqueXPath(fsXpath)) return fsXpath;
      }
      if (["input", "select", "textarea"].includes(tag) && el.id) {
        const labelFor = `//label[@for="${el.id}"]/following-sibling::${tag}`;
        if (isUniqueXPath(labelFor)) return labelFor;
        const labelAncestor = `//label[descendant::${tag}[@id="${el.id}"]]`;
        if (isUniqueXPath(labelAncestor)) return labelAncestor;
      }
      let parent = el.parentElement;
      if (parent) {
        const parentTag = parent.tagName.toLowerCase();
        if (parent.id) {
          const pxpath = `//*[@id="${parent.id}"]/${tag}`;
          if (isUniqueXPath(pxpath)) return pxpath;
        }
        if (parent.classList && parent.classList.length) {
          for (const pc of parent.classList) {
            const pxpath = `//${parentTag}[contains(@class,"${pc}")]/${tag}`;
            if (isUniqueXPath(pxpath)) return pxpath;
          }
        }
        let idx = 1, sib = el;
        while (sib = sib.previousElementSibling) idx++;
        if (idx > 1) {
          const psXpath = `//${tag}[${idx}]`;
          if (isUniqueXPath(psXpath)) return psXpath;
        }
      }
      return getAbsoluteXPath(el);
    }

    function getSuggestedName(el) {
      return (
        el.getAttribute('aria-label') ||
        el.name ||
        el.id ||
        el.getAttribute('data-testid') ||
        el.placeholder ||
        el.getAttribute('title') ||
        el.tagName.toLowerCase()
      );
    }

    function getElementType(el) {
      const tag = el.tagName.toLowerCase();
      if (tag === "input") {
        const type = el.type ? el.type.toLowerCase() : "text";
        if (type === "password") return "password";
        if (type === "checkbox") return "checkbox";
        if (type === "radio") return "radio";
        if (type === "submit") return "button";
        if (type === "text" || type === "email" || type === "number") return "textbox";
        return type;
      }
      if (tag === "textarea") return "textarea";
      if (tag === "select") return "dropdown";
      if (tag === "button") return "button";
      if (tag === "a") return "link";
      return tag;
    }

    function getFrameChain() {
      // Simple: not tracking frames in this implementation (but placeholder for frame chain logic)
      return "";
    }

    function getWindowNumber() { return 1; }
    function getWindowTitle() { return document.title || ""; }

    function generateLocators(el) {
      const tag = el.tagName.toLowerCase();
      const locators = [];
      if (el.id && isUniqueXPath(`//*[@id="${el.id}"]`)) {
        locators.push({ locator: `//*[@id="${el.id}"]`, locatorType: "id" });
      }
      if (el.name && isUniqueXPath(`//${tag}[@name="${el.name}"]`)) {
        locators.push({ locator: `//${tag}[@name="${el.name}"]`, locatorType: "name" });
      }
      Array.from(el.attributes).forEach(attr => {
        if (attr.name.startsWith("data-") && attr.value) {
          let xpath = `//${tag}[contains(@${attr.name}, "${attr.value}")]`;
          if (isUniqueXPath(xpath)) {
            locators.push({ locator: xpath, locatorType: attr.name });
          }
        }
      });
      if (el.classList && el.classList.length) {
        Array.from(el.classList).forEach(className => {
          let xpath = `//${tag}[contains(concat(' ',normalize-space(@class),' '),' ${className} ')]`;
          if (isUniqueXPath(xpath)) {
            locators.push({ locator: xpath, locatorType: "class" });
          }
          let ancestorXpath = `//${tag}[ancestor::*[contains(@class, "${className}")]]`;
          if (isUniqueXPath(ancestorXpath)) {
            locators.push({ locator: ancestorXpath, locatorType: "ancestor-class" });
          }
        });
      }
      ["aria-label", "placeholder", "title"].forEach(attr => {
        if (el.getAttribute(attr)) {
          let v = el.getAttribute(attr).trim();
          let xpath = `//${tag}[normalize-space(@${attr})="${v}"]`;
          if (isUniqueXPath(xpath)) {
            locators.push({ locator: xpath, locatorType: attr });
          }
        }
      });
      let text = (el.textContent || "").trim();
      if (text && text.length < 50) {
        let textXpath = `//${tag}[normalize-space(text())="${text}"]`;
        if (isUniqueXPath(textXpath)) locators.push({ locator: textXpath, locatorType: "text-exact" });
        let containsXpath = `//${tag}[contains(normalize-space(text()), "${text.split(' ')[0]}")]`;
        if (isUniqueXPath(containsXpath)) locators.push({ locator: containsXpath, locatorType: "text-contains" });
        let fsXpath = `//${tag}[following-sibling::*[normalize-space(text())="${text}"]]`;
        if (isUniqueXPath(fsXpath)) locators.push({ locator: fsXpath, locatorType: "following-sibling-text" });
      }
      if (["input", "select", "textarea"].includes(tag) && el.id) {
        let labelByFor = `//label[@for="${el.id}"]/following-sibling::${tag}`;
        if (isUniqueXPath(labelByFor)) locators.push({ locator: labelByFor, locatorType: "label-for" });
        let labelAncestor = `//label[descendant::${tag}[@id="${el.id}"]]`;
        if (isUniqueXPath(labelAncestor)) locators.push({ locator: labelAncestor, locatorType: "label-ancestor" });
      }
      let parent = el.parentElement;
      if (parent) {
        let parentTag = parent.tagName.toLowerCase();
        if (parent.id) {
          let pxpath = `//*[@id="${parent.id}"]/${tag}`;
          if (isUniqueXPath(pxpath)) locators.push({ locator: pxpath, locatorType: "parent-id" });
        }
        if (parent.classList && parent.classList.length) {
          for (const pc of parent.classList) {
            let pxpath = `//${parentTag}[contains(@class,"${pc}")]/${tag}`;
            if (isUniqueXPath(pxpath)) locators.push({ locator: pxpath, locatorType: "parent-class" });
          }
        }
        let idx = 1, sib = el;
        while (sib = sib.previousElementSibling) idx++;
        if (idx > 1) {
          let psXpath = `//${tag}[${idx}]`;
          if (isUniqueXPath(psXpath)) locators.push({ locator: psXpath, locatorType: "nth" });
        }
      }
      locators.push({ locator: getAbsoluteXPath(el), locatorType: "absolute" });
      const seen = new Set();
      return locators.filter(l => {
        if (seen.has(l.locator)) return false;
        seen.add(l.locator);
        return true;
      });
    }

    // --- Main persistent recorder logic ---
    if (!window.__robustRecorderInstalled) {
        window.__robustRecorderInstalled = true;
        if (!localStorage.getItem("robustRecordedActions")) {
            localStorage.setItem("robustRecordedActions", "[]");
        }
        window.recordedActions = JSON.parse(localStorage.getItem("robustRecordedActions") || "[]");

        function saveActions() {
            localStorage.setItem("robustRecordedActions", JSON.stringify(window.recordedActions));
        }

        function recordAction(type, e) {
            var el = e && e.target;
            if (!el || !el.tagName) return;
            var tag = el.tagName.toLowerCase();
            var action = {
                objectName: getSuggestedName(el) + "_" + getElementType(el),
                suggestedName: getSuggestedName(el),
                elementType: getElementType(el),
                locator: generateLocators(el)[0]?.locator || "",
                locatorType: generateLocators(el)[0]?.locatorType || "",
                locatorSuggestions: generateLocators(el),
                windowTitle: getWindowTitle(),
                frameChain: getFrameChain(),
                timestamp: new Date().toISOString(),
                targetElement: el.outerHTML,
                actualValue: el.value || '',
                eventType: type
            };
            window.recordedActions.push(action);
            saveActions();
        }

        document.addEventListener('click', e => recordAction('click', e), true);
        document.addEventListener('input', e => recordAction('input', e), true);
        document.addEventListener('change', e => recordAction('change', e), true);
        document.addEventListener('blur', e => recordAction('blur', e), true);
        document.addEventListener('keydown', function(e){
            if (e.key === 'Enter') recordAction('enter', e);
        }, true);

        window.addEventListener("load", function() {
            window.recordedActions = JSON.parse(localStorage.getItem("robustRecordedActions") || "[]");
        });

        window.clearRecordedActions = function() {
            window.recordedActions = [];
            localStorage.setItem('robustRecordedActions', "[]");
        };
    }
})();
"""

class SeleniumSessionManager:
    def __init__(self):
        self.sessions = {}
        self.keepalive_threads = {}

    def launch_browser(self, url, session_id):
        options = webdriver.ChromeOptions()
        options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(2)
        self._inject_js_all_windows_and_frames(driver)
        self.sessions[session_id] = driver
        self.start_keepalive_monitor(session_id)
        return session_id

    def inject_recorder(self, session_id):
        driver = self.get_driver(session_id)
        if driver:
            try:
                self._inject_js_all_windows_and_frames(driver)
                return True
            except Exception as e:
                print(f"Failed to inject recorder JS: {e}")
                return False
        return False

    def get_driver(self, session_id):
        return self.sessions.get(session_id)

    def get_actions(self, session_id):
        driver = self.get_driver(session_id)
        if driver:
            try:
                actions = driver.execute_script("return JSON.parse(localStorage.getItem('robustRecordedActions') || '[]');")
                return {"actions": actions}
            except Exception as e:
                return {"actions": [], "error": str(e)}
        return {"actions": [], "error": "No session/driver"}

    def clear_actions(self, session_id):
        driver = self.get_driver(session_id)
        if driver:
            driver.execute_script("localStorage.setItem('robustRecordedActions', '[]'); window.recordedActions = [];")
            return {"status": "success"}
        return {"status": "failed"}

    def _inject_js_all_windows_and_frames(self, driver):
        original_window = driver.current_window_handle
        for window_handle in driver.window_handles:
            driver.switch_to.window(window_handle)
            self._inject_js_all_frames(driver)
        driver.switch_to.window(original_window)

    def _inject_js_all_frames(self, driver):
        self._inject_js_current_frame_and_children(driver, [])

    def _inject_js_current_frame_and_children(self, driver, frame_chain):
        try:
            driver.execute_script(RECORDER_JS)
        except Exception as e:
            print(f"JS inject error (framechain {frame_chain}): {e}")
        frames = driver.find_elements("tag name", "iframe") + driver.find_elements("tag name", "frame")
        for idx, frame in enumerate(frames):
            try:
                driver.switch_to.frame(frame)
                self._inject_js_current_frame_and_children(driver, frame_chain + [idx])
                driver.switch_to.parent_frame()
            except Exception as e:
                print(f"Could not inject JS into frame {idx} (framechain {frame_chain}): {e}")

    def start_keepalive_monitor(self, session_id):
        if session_id in self.keepalive_threads:
            return

        def is_interactable(element):
            try:
                return element.is_displayed() and element.is_enabled()
            except Exception:
                return False

        def keepalive_job():
            driver = self.get_driver(session_id)
            while True:
                try:
                    for keyword in ['session', 'keep alive', 'continue', 'still there', 'timeout']:
                        modals = driver.find_elements(
                            "xpath",
                            "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{}')]".format(keyword)
                        )
                        for modal in modals:
                            try:
                                btns = modal.find_elements("xpath", ".//button|.//input[@type='button' or @type='submit']")
                                for btn in btns:
                                    if is_interactable(btn):
                                        btn.click()
                                        driver.execute_script("""
                                        window.recordedActions = window.recordedActions || [];
                                        window.recordedActions.push({
                                            objectName: "keepalive_button",
                                            eventType: "keepalive",
                                            locator: arguments[0].outerHTML,
                                            locatorType: "auto",
                                            timestamp: new Date().toISOString(),
                                            targetElement: arguments[0].outerHTML,
                                            actualValue: "",
                                            windowTitle: document.title,
                                            frameChain: "",
                                            elementType: "keepalive",
                                            suggestedName: "keepalive",
                                            locatorSuggestions: []
                                        });
                                        var actions = JSON.parse(localStorage.getItem('robustRecordedActions') || "[]");
                                        actions.push({
                                            objectName: "keepalive_button",
                                            eventType: "keepalive",
                                            locator: arguments[0].outerHTML,
                                            locatorType: "auto",
                                            timestamp: new Date().toISOString(),
                                            targetElement: arguments[0].outerHTML,
                                            actualValue: "",
                                            windowTitle: document.title,
                                            frameChain: "",
                                            elementType: "keepalive",
                                            suggestedName: "keepalive",
                                            locatorSuggestions: []
                                        });
                                        localStorage.setItem('robustRecordedActions', JSON.stringify(actions));
                                        """, btn)
                                        print(f"[KEEPALIVE] Clicked keepalive button for session {session_id}.")
                                        break
                                else:
                                    if is_interactable(modal):
                                        modal.click()
                                        driver.execute_script("""
                                        window.recordedActions = window.recordedActions || [];
                                        window.recordedActions.push({
                                            objectName: "keepalive_modal",
                                            eventType: "keepalive",
                                            locator: arguments[0].outerHTML,
                                            locatorType: "auto",
                                            timestamp: new Date().toISOString(),
                                            targetElement: arguments[0].outerHTML,
                                            actualValue: "",
                                            windowTitle: document.title,
                                            frameChain: "",
                                            elementType: "keepalive",
                                            suggestedName: "keepalive",
                                            locatorSuggestions: []
                                        });
                                        var actions = JSON.parse(localStorage.getItem('robustRecordedActions') || "[]");
                                        actions.push({
                                            objectName: "keepalive_modal",
                                            eventType: "keepalive",
                                            locator: arguments[0].outerHTML,
                                            locatorType: "auto",
                                            timestamp: new Date().toISOString(),
                                            targetElement: arguments[0].outerHTML,
                                            actualValue: "",
                                            windowTitle: document.title,
                                            frameChain: "",
                                            elementType: "keepalive",
                                            suggestedName: "keepalive",
                                            locatorSuggestions: []
                                        });
                                        localStorage.setItem('robustRecordedActions', JSON.stringify(actions));
                                        """, modal)
                                        print(f"[KEEPALIVE] Clicked keepalive modal for session {session_id}.")
                            except Exception as e:
                                if is_interactable(modal):
                                    print(f"[KEEPALIVE] Error clicking visible keepalive element: {e}")
                    time.sleep(3)
                except (WebDriverException, NoSuchElementException):
                    break
                except Exception as e:
                    print(f"[KEEPALIVE-THREAD] Exception: {e}")
                    time.sleep(3)

        t = threading.Thread(target=keepalive_job, daemon=True)
        t.start()
        self.keepalive_threads[session_id] = t
