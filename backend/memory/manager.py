from memory.memory import Memory


class MemoryManager:

    def __init__(self):

        self.memory = Memory()

    # -----------------------------
    # Conversation
    # -----------------------------

    def add_user_message(self, message: str):

        self.memory.remember_conversation(

            "user",

            message

        )

    def add_assistant_message(self, message: str):

        self.memory.remember_conversation(

            "assistant",

            message

        )

    def get_messages(self):

        return self.memory.recent_conversation(

            limit=100000

        )

    def clear_messages(self):

        self.memory.conversation.clear()

    # -----------------------------
    # Profile
    # -----------------------------

    def remember(self, key: str, value: str):

        return self.memory.remember(

            key,

            value

        )

    def recall(self, key: str):

        return self.memory.recall(

            key

        )

    def get_profile(self):

        return self.memory.profile.get_profile()

    # -----------------------------
    # Utility
    # -----------------------------

    def stats(self):

        return self.memory.stats()

    def clear(self):

        self.memory.reset()