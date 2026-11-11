import re

from brain.entity import EntityExtractor


class IntentEngine:
    """
    Detects user intent and extracts entities.
    """

    def __init__(self):

        self.entity = EntityExtractor()

        self.patterns = (

            # -----------------------------
            # WEB (must win over open_app)
            # -----------------------------

            (
                "open_website",
                (
                    r"open\s+(?:website\s+)?([\w-]+\.[a-z]{2,}(?:/\S*)?)",
                    r"visit\s+(.+)",
                )
            ),

            (
                "search_web",
                (
                    r"search(?:\s+for)?\s+(.+)",
                    r"google\s+(.+)",
                    r"find\s+(.+)",
                )
            ),

            # -----------------------------
            # APPS
            # -----------------------------

            (
                "open_app",
                (
                    r"open\s+(.+)",
                    r"launch\s+(.+)",
                    r"start\s+(.+)",
                )
            ),

            (
                "close_app",
                (
                    r"close\s+(.+)",
                    r"exit\s+(.+)",
                    r"quit\s+(.+)",
                )
            ),

            # -----------------------------
            # MEMORY RECALL
            # -----------------------------

            (
                "recall",
                (
                    r"what(?:'s| is| was)? my\s+.+",
                    r"who am i",
                    r"where do i live",
                    r"which is my\s+.+",
                    r"tell me my\s+.+",
                    r"do you (?:know|remember) my\s+.+",
                    r"what do you (?:remember|know about me)",
                    r"recall",
                )
            ),

            # -----------------------------
            # MEMORY SAVE
            # -----------------------------

            (
                "remember",
                (
                    r"remember\s+(.+)",
                    r"my\s+.+?\s+(?:is|are)\s+.+",
                    r"i live in\s+.+",
                    r"i(?:'m| am) from\s+.+",
                    r"i(?:'m| am)\s+(?:a|an)\s+.+",
                    r"call me\s+.+",
                )
            ),

            # -----------------------------
            # SYSTEM
            # -----------------------------

            (
                "system_status",
                (
                    r"system status",
                    r"cpu",
                    r"ram",
                    r"memory",
                    r"battery",
                )
            ),
        )

    def detect(self, text: str):

        original = (text or "").strip()

        lower = original.lower()

        entities = self.entity.extract_all(original)

        for intent, regex_list in self.patterns:

            for pattern in regex_list:

                match = re.match(pattern, lower)

                if not match:

                    continue

                target = ""

                if match.groups():

                    target = (match.group(1) or "").strip()

                return {
                    "intent": intent,
                    "text": lower,
                    "target": target,
                    "entities": entities,
                }

        return {
            "intent": "chat",
            "text": lower,
            "target": "",
            "entities": entities,
        }
