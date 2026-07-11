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

        # --------------------------------
        # OPEN APP
        # --------------------------------

        if intent == "open_app":

            return apps.open_app(target)

        # --------------------------------

        if intent == "close_app":

            return apps.close_app(target)

        # --------------------------------

        if intent == "search_web":

            return browser.google_search(target)

        # --------------------------------

        if intent == "open_website":

            return browser.open_website(target)

        # --------------------------------

        if intent == "system_status":

            return system.system_status()

        # --------------------------------
        # MEMORY
        # --------------------------------

        if intent == "remember":

            if field and value:

                if field in (

                    "name",

                    "email",

                    "city",

                    "occupation"

                ):

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

                "message": "Nothing to remember."

            }

        # --------------------------------
        # RECALL
        # --------------------------------

        if intent == "recall":

            text = command["text"]

            profile = self.memory.profile.get_profile()

            if "name" in text:

                name = profile["name"]

                return {

                    "success": True,

                    "message": f"Your name is {name}."

                    if name else

                    "I don't know your name yet."

                }

            if "city" in text or "live" in text:

                city = profile["city"]

                return {

                    "success": True,

                    "message": f"You live in {city}."

                    if city else

                    "I don't know where you live."

                }

            if "email" in text:

                email = profile["email"]

                return {

                    "success": True,

                    "message": email

                    if email else

                    "I don't know your email."

                }

            if "occupation" in text:

                job = profile["occupation"]

                return {

                    "success": True,

                    "message": job

                    if job else

                    "I don't know your occupation."

                }

            return {

                "success": True,

                "profile": profile

            }

        # --------------------------------
        # AI
        # --------------------------------

        return {

            "success": False,

            "message": "Forward to AI."

        }