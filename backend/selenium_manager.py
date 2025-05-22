from selenium import webdriver

class SeleniumSessionManager:
    def __init__(self):
        self.sessions = {}

    def launch_browser(self, url):
        options = webdriver.ChromeOptions()
        options.add_experimental_option("detach", True)
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        session_id = id(driver)
        self.sessions[session_id] = driver
        return session_id

    def close_session(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id].quit()
            del self.sessions[session_id]
