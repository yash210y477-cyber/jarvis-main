from brain.facts import canonical_key, human_key

from memory.memory import Memory

from tools import apps
from tools import browser
from tools import system


RECALL_FIELDS = (
    ("name", ("name",)),
    ("city", ("city", "live", "from")),
    ("email", ("email", "e-mail")),
    ("occupation", ("occupation", "job", "work")),
    ("favourite_language", ("language",)),
    ("editor", ("editor",)),
    ("bike", ("bike",)),
    ("phone", ("phone",)),
    ("laptop", ("laptop",)),
)

RECALL_ALL_WORDS = ("remember", "know about me", "memory", "everything")


class Router:

    def __init__(self, memory=None):

        self.memory = memory or Memory()

    def route(self, command: dict):

        intent = command.get("intent")

        target = command.get("target", "")

        text = (command.get("text") or "").lower()

        # -----------------------------------
        # DESKTOP / WEB
        # -----------------------------------

        if intent == "open_app":

            return apps.open_app(target)

        if intent == "close_app":

            return apps.close_app(target)

        if intent == "search_web":

            return browser.google_search(target)

        if intent == "open_website":

            return browser.open_website(target)

        if intent == "system_status":

            return system.system_status()

        # -----------------------------------
        # MEMORY SAVE
        # -----------------------------------

        if intent == "remember":

            return self._remember(command)

        # -----------------------------------
        # MEMORY RECALL
        # -----------------------------------

        if intent == "recall":

            return self._recall(text)

        return {
            "success": False,
            "message": "Forward to AI."
        }

    # -----------------------------------
    # REMEMBER
    # -----------------------------------

    def _remember(self, command: dict):

        entities = list(command.get("entities") or [])

        field = command.get("field")

        value = command.get("value")

        if not entities and field and value:

            entities = [{"field": field, "value": value}]

        if not entities:

            return {
                "success": False,
                "message": "Nothing to remember."
            }

        remembered = []

        for entity in entities:

            key = canonical_key(entity.get("field")) or entity.get("field")

            item = (entity.get("value") or "").strip()

            if not key or not item:

                continue

            result = self.memory.remember(key, item)

            if result.get("success"):

                remembered.append({"field": key, "value": item})

        if not remembered:

            return {
                "success": False,
                "message": "Nothing to remember."
            }

        parts = [
            f"your {human_key(item['field'])} is {item['value']}"
            for item in remembered
        ]

        return {
            "success": True,
            "message": "Got it — I'll remember " + ", ".join(parts) + ".",
            "remembered": remembered,
        }

    # -----------------------------------
    # RECALL
    # -----------------------------------

    def _recall(self, text: str):

        for key, words in RECALL_FIELDS:

            if any(word in text for word in words):

                value = self.memory.recall(key)

                return {
                    "success": True,
                    "message": self._describe(key, value),
                    "field": key,
                }

        if any(word in text for word in RECALL_ALL_WORDS):

            return self._recall_all()

        return {
            "success": True,
            "profile": self.memory.profile.get_profile()
        }

    def _describe(self, key: str, value) -> str:

        human = human_key(key)

        if key == "name":

            return f"Your name is {value}." if value else "I don't know your name."

        if key == "city":

            return f"You live in {value}." if value else "I don't know your city."

        if key == "email":

            return value if value else "I don't know your email."

        if key == "occupation":

            return value if value else "I don't know your occupation."

        if value:

            return f"Your {human} is {value}."

        return f"I don't know your {human}."

    def _recall_all(self):

        lines = []

        profile = self.memory.profile.get_profile()

        for key in ("name", "email", "city", "occupation"):

            if profile.get(key):

                lines.append(f"- {human_key(key)}: {profile[key]}")

        for item in self.memory.all_facts():

            if item.get("key") and item.get("value"):

                lines.append(
                    f"- {human_key(item['key'])}: {item['value']}"
                )

        if not lines:

            return {
                "success": True,
                "message": "I don't remember anything about you yet."
            }

        return {
            "success": True,
            "message": "Here is what I remember:\n" + "\n".join(lines)
        }
