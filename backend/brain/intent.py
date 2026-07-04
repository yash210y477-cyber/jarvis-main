import re


class IntentEngine:
    """
    Responsible for identifying the user's intent
    from a text command.
    """

    def __init__(self):
        self.patterns = {
            "open_app": [
                r"open\s+(.+)",
                r"launch\s+(.+)",
                r"start\s+(.+)",
            ],

            "close_app": [
                r"close\s+(.+)",
                r"exit\s+(.+)",
                r"quit\s+(.+)",
            ],

            "search_web": [
                r"search\s+(.+)",
                r"google\s+(.+)",
                r"find\s+(.+)",
            ],

            "open_website": [
                r"open website\s+(.+)",
                r"visit\s+(.+)",
            ],

            "remember": [
                r"remember\s+(.+)",
            ],

            "recall": [
                r"what do you remember",
                r"recall",
                r"remembered",
            ],

            "system_status": [
                r"system status",
                r"cpu",
                r"ram",
                r"memory",
                r"battery",
            ]
        }

    def detect(self, text: str):

        text = text.lower().strip()

        for intent, regex_list in self.patterns.items():

            for pattern in regex_list:

                match = re.match(pattern, text)

                if match:

                    target = ""

                    if match.groups():
                        target = match.group(1).strip()

                    return {
                        "intent": intent,
                        "target": target,
                        "text": text
                    }

        return {
            "intent": "chat",
            "target": "",
            "text": text
        }