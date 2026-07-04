import re

from brain.entity import EntityExtractor


class IntentEngine:
    """
    Detects user intent and extracts entities.
    """

    def __init__(self):

        self.entity = EntityExtractor()

        self.patterns = {

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

            "search_web": [
                r"search\s+(.+)",
                r"google\s+(.+)",
                r"find\s+(.+)"
            ],

            "open_website": [
                r"open website\s+(.+)",
                r"visit\s+(.+)"
            ],

            "remember": [
                r"remember(.+)",
                r"my name is(.+)",
                r"i live in(.+)",
                r"my email is(.+)",
                r"i am(.+)",
                r"my favourite editor is(.+)",
                r"i use(.+)"
            ],

            "recall": [
                r"what is my name",
                r"who am i",
                r"where do i live",
                r"what do you remember",
                r"recall"
            ],

            "system_status": [
                r"system status",
                r"cpu",
                r"ram",
                r"memory",
                r"battery"
            ]
        }

    def detect(self, text: str):

        text = text.strip().lower()

        entities = self.entity.extract(text)

        for intent, regex_list in self.patterns.items():

            for pattern in regex_list:

                match = re.match(pattern, text)

                if match:

                    result = {

                        "intent": intent,

                        "text": text,

                        "target": ""
                    }

                    if match.groups():

                        result["target"] = match.group(1).strip()

                    result.update(entities)

                    return result

        return {

            "intent": "chat",

            "text": text,

            "target": "",

            **entities
        }