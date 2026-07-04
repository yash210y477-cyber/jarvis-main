from tools import apps
from tools import browser
from tools import system

from memory.memory import Memory


class Router:

    def __init__(self):

        self.memory = Memory()

    def route(self, command: dict):

        intent = command.get("intent")

        target = command.get("target", "")

        field = command.get("field")

        value = command.get("value")

        # -----------------------------
        # Desktop Apps
        # -----------------------------

        if intent == "open_app":

            return apps.open_app(target)

        if intent == "close_app":

            return apps.close_app(target)

        # -----------------------------
        # Browser
        # -----------------------------

        if intent == "search_web":

            return browser.google_search(target)

        if intent == "open_website":

            return browser.open_website(target)

        # -----------------------------
        # System
        # -----------------------------

        if intent == "system_status":

            return system.system_status()

        # -----------------------------
        # Remember
        # -----------------------------

        if intent == "remember":

            if field and value:

                if field in [
                    "name",
                    "email",
                    "city",
                    "occupation"
                ]:

                    self.memory.profile.update(
                        field,
                        value
                    )

                elif field == "editor":

                    data = self.memory.profile.storage.read()

                    data["preferences"]["editor"] = value

                    self.memory.profile.storage.write(data)

                return {
                    "success": True,
                    "message": f"I'll remember your {field}."
                }

            return {
                "success": False,
                "message": "I couldn't understand what to remember."
            }

        # -----------------------------
        # Recall
        # -----------------------------

        if intent == "recall":

            text = command.get("text", "")

            if "name" in text:

                name = self.memory.profile.get("name")

                if name:

                    return {
                        "success": True,
                        "message": f"Your name is {name}."
                    }

            if "live" in text or "city" in text:

                city = self.memory.profile.get("city")

                if city:

                    return {
                        "success": True,
                        "message": f"You live in {city}."
                    }

            profile = self.memory.profile.get_profile()

            return {
                "success": True,
                "profile": profile
            }

        # -----------------------------
        # AI
        # -----------------------------

        return {
            "success": False,
            "message": "Forward to AI."
        }