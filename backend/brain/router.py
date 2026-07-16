from tools import apps
from tools import browser
from tools import system

from memory.memory import Memory


class Router:

    def __init__(self):

        self.memory = Memory()

        self.recall_map = {

            "name": (
                "name",
                "Your name is {}.",
                "I don't know your name."
            ),

            "city": (
                "city",
                "You live in {}.",
                "I don't know your city."
            ),

            "live": (
                "city",
                "You live in {}.",
                "I don't know your city."
            ),

            "email": (
                "email",
                "{}",
                "I don't know your email."
            ),

            "occupation": (
                "occupation",
                "{}",
                "I don't know your occupation."
            ),

            "language": (
                "favourite_language",
                "{}",
                "I don't know your favourite language."
            ),

            "editor": (
                "editor",
                "{}",
                "I don't know your favourite editor."
            ),

            "bike": (
                "bike",
                "{}",
                "I don't know your bike."
            ),

            "phone": (
                "phone",
                "{}",
                "I don't know your phone."
            ),

            "laptop": (
                "laptop",
                "{}",
                "I don't know your laptop."
            )

        }

    def route(self, command: dict):
        

        intent = command.get("intent")

        target = command.get("target", "")

        field = command.get("field")

        value = command.get("value")

        text = str(command.get("text", "")).lower()

        # -----------------------------------
        # OPEN APP
        # -----------------------------------

        if intent == "open_app":
            
            result = apps.open_app(target)
            
            return result
        # -----------------------------------
        # CLOSE APP
        # -----------------------------------

        if intent == "close_app":

            return apps.close_app(target)

        # -----------------------------------
        # SEARCH WEB
        # -----------------------------------

        if intent == "search_web":

            return browser.google_search(target)

        # -----------------------------------
        # OPEN WEBSITE
        # -----------------------------------

        if intent == "open_website":

            return browser.open_website(target)

        # -----------------------------------
        # SYSTEM STATUS
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

            return self.memory.remember(

                field,

                value

            )

        # -----------------------------------
        # RECALL
        # -----------------------------------

        if intent == "recall":

            for keyword, config in self.recall_map.items():

                if keyword in text:

                    memory_key, success_msg, fail_msg = config

                    stored = self.memory.recall(

                        memory_key

                    )

                    return {

                        "success": True,

                        "message":

                            success_msg.format(stored)

                            if stored else

                            fail_msg

                    }

            return {

                "success": True,

                "profile":

                    self.memory.profile.get_profile()

            }
        
        # -----------------------------------
        # AI FALLBACK
        # -----------------------------------

        return {

            "success": False,

            "message": "Forward to AI."

        }