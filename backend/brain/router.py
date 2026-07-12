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

        text = command.get("text", "").lower()

        # -----------------------------------
        # OPEN APP
        # -----------------------------------

        if intent == "open_app":

            return apps.open_app(target)

        # -----------------------------------

        if intent == "close_app":

            return apps.close_app(target)

        # -----------------------------------

        if intent == "search_web":

            return browser.google_search(target)

        # -----------------------------------

        if intent == "open_website":

            return browser.open_website(target)

        # -----------------------------------

        if intent == "system_status":

            return system.system_status()

        # -----------------------------------
        # REMEMBER
        # -----------------------------------

        if intent == "remember":

            if not field or not value:

                return {

                    "success": False,

                    "message": "Nothing to remember."

                }

            result = self.memory.remember(

                field,

                value

            )

            return result

        # -----------------------------------
        # RECALL
        # -----------------------------------

        if intent == "recall":

            if "name" in text:

                value = self.memory.recall("name")

                return {

                    "success": True,

                    "message":

                        f"Your name is {value}."

                        if value else

                        "I don't know your name."

                }

            if "city" in text or "live" in text:

                value = self.memory.recall("city")

                return {

                    "success": True,

                    "message":

                        f"You live in {value}."

                        if value else

                        "I don't know your city."

                }

            if "email" in text:

                value = self.memory.recall("email")

                return {

                    "success": True,

                    "message":

                        value

                        if value else

                        "I don't know your email."

                }

            if "occupation" in text:

                value = self.memory.recall("occupation")

                return {

                    "success": True,

                    "message":

                        value

                        if value else

                        "I don't know your occupation."

                }

            if "language" in text:

                value = self.memory.recall(

                    "favourite_language"

                )

                return {

                    "success": True,

                    "message":

                        value

                        if value else

                        "I don't know your favourite language."

                }

            if "editor" in text:

                value = self.memory.recall(

                    "editor"

                )

                return {

                    "success": True,

                    "message":

                        value

                        if value else

                        "I don't know your favourite editor."

                }

            if "bike" in text:

                value = self.memory.recall(

                    "bike"

                )

                return {

                    "success": True,

                    "message":

                        value

                        if value else

                        "I don't know your bike."

                }

            if "phone" in text:

                value = self.memory.recall(

                    "phone"

                )

                return {

                    "success": True,

                    "message":

                        value

                        if value else

                        "I don't know your phone."

                }

            if "laptop" in text:

                value = self.memory.recall(

                    "laptop"

                )

                return {

                    "success": True,

                    "message":

                        value

                        if value else

                        "I don't know your laptop."

                }

            return {

                "success": True,

                "profile":

                    self.memory.profile.get_profile()

            }

        # -----------------------------------
        # AI
        # -----------------------------------

        return {

            "success": False,

            "message": "Forward to AI."

        }