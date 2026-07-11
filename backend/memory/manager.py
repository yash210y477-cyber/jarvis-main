import re

from memory.memory import Memory


class MemoryManager:

    def __init__(self):

        self.memory = Memory()

    def add_user_message(self, message: str):

        self.memory.conversation.add(

            "user",

            message

        )

        self.extract_profile(message)

    def add_assistant_message(self, message: str):

        self.memory.conversation.add(

            "assistant",

            message

        )

    def get_messages(self):

        return self.memory.conversation.last()

    def clear(self):

        self.memory.reset()

    def extract_profile(self, text: str):

        text = text.strip()

        patterns = [

            r"my name is (.+)",

            r"i am (.+)",

            r"i'm (.+)"

        ]

        lower = text.lower()

        for pattern in patterns:

            match = re.search(pattern, lower)

            if match:

                name = match.group(1).strip().title()

                self.memory.profile.update(

                    "name",

                    name

                )

                break