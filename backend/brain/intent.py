import re

from brain.entity import EntityExtractor


class IntentEngine:
    """
    Detects user intent and extracts entities.
    """

    def __init__(self):

        self.entity = EntityExtractor()

        self.patterns = {

            # -----------------------------
            # APPS
            # -----------------------------

            "open_app": [
                r"open\s+(.+)",
                r"launch\s+(.+)",
                r"start\s+(.+)"
            ],

            "close_app": [
                r"close\s+(.+)",
                r"exit\s+(.+)",
                r"quit\s+(.+)"
            ],

            # -----------------------------
            # WEB
            # -----------------------------

            "search_web": [
                r"search\s+(.+)",
                r"google\s+(.+)",
                r"find\s+(.+)"
            ],

            "open_website": [
                r"open website\s+(.+)",
                r"visit\s+(.+)"
            ],

            # -----------------------------
            # MEMORY SAVE
            # -----------------------------

            "remember": [

                r"remember(.+)",

                r"my name is(.+)",

                r"i live in(.+)",

                r"my city is(.+)",

                r"my email is(.+)",

                r"i am(.+)",

                r"my occupation is(.+)",

                r"my favourite language is(.+)",

                r"my favorite language is(.+)",

                r"my favourite editor is(.+)",

                r"my favorite editor is(.+)",

                r"i use(.+)",

                r"my bike is(.+)",

                r"my phone is(.+)",

                r"my laptop is(.+)"
            ],

            # -----------------------------
            # MEMORY RECALL
            # -----------------------------

            "recall": [

                r"what is my name",

                r"who am i",

                r"where do i live",

                r"what is my city",

                r"what is my email",

                r"what is my occupation",

                r"what is my favourite language",

                r"what is my favorite language",

                r"what is my favourite editor",

                r"what is my favorite editor",

                r"what is my bike",

                r"what is my phone",

                r"what is my laptop",

                r"what do you remember",

                r"recall"

            ],

            # -----------------------------
            # SYSTEM
            # -----------------------------

            "system_status": [

                r"system status",

                r"cpu",

                r"ram",

                r"memory",

                r"battery"

            ]

        }

    def detect(self, text: str):

        original = text.strip()

        lower = original.lower()

        entities = self.entity.extract(original)

        for intent, regex_list in self.patterns.items():

            for pattern in regex_list:

                match = re.match(pattern, lower)

                if match:

                    result = {

                        "intent": intent,

                        "text": lower,

                        "target": ""

                    }

                    if match.groups():

                        result["target"] = match.group(1).strip()

                    result.update(entities)

                    return result

        return {

            "intent": "chat",

            "text": lower,

            "target": "",

            **entities

        }