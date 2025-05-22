from ai_xpath import get_ai_xpath_suggestions

class ObjectRepositoryManager:
    def __init__(self, repo=None):
        self.repo = repo if repo is not None else []

    def add_object(self, obj):
        obj['suggested_locators'] = get_ai_xpath_suggestions(obj)
        self.repo.append(obj)

    def to_json(self):
        return self.repo
