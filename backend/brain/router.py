from tools import apps
from tools import browser
from tools import system
from memory.memory import Memory


class Router:

    def __init__(self):
        self.memory = Memory()

    def route(self, command: dict):

        intent = command["intent"]
        target = command["target"]
        text = command["text"]

        if intent == "open_app":
            return apps.open_app(target)

        elif intent == "close_app":
            return apps.close_app(target)

        elif intent == "search_web":
            return browser.google_search(target)

        elif intent == "open_website":
            return browser.open_website(target)

        elif intent == "system_status":
            return system.system_status()

        elif intent == "remember":
            self.memory.remember(text.replace("remember", "").strip())

            return {
                "success": True,
                "message": "Memory saved."
            }

        elif intent == "recall":
            return {
                "success": True,
                "memory": self.memory.recall()
            }

        return {
            "success": False,
            "message": "Forward to AI."
        }