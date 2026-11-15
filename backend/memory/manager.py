from memory.memory import Memory


class MemoryManager:

    def __init__(self, memory=None):

        self.memory = memory or Memory()

    # -----------------------------
    # Conversation
    # -----------------------------

    def add_user_message(self, message: str):

        self.memory.remember_conversation("user", message)

    def add_assistant_message(self, message: str):

        self.memory.remember_conversation("assistant", message)

    def get_messages(self):

        return self.memory.recent_conversation(limit=100000)

    def message_count(self) -> int:

        return self.memory.message_count()

    # -----------------------------
    # Chat history (dated)
    # -----------------------------

    def chats(self, limit: int = 60) -> list:

        return self.memory.chats(limit)

    def chat_messages(self, chat_id) -> list:

        return self.memory.chat_messages(chat_id)

    def start_chat(self, title: str = "") -> int:

        return self.memory.start_chat(title)

    def delete_chat(self, chat_id) -> bool:

        return self.memory.delete_chat(chat_id)

    def trim_messages(self, keep: int) -> int:

        return self.memory.trim_conversation(keep)

    def clear_messages(self):

        self.memory.conversation.clear()

    # -----------------------------
    # Profile
    # -----------------------------

    def remember(self, key: str, value: str):

        return self.memory.remember(key, value)

    def recall(self, key: str):

        return self.memory.recall(key)

    def get_profile(self):

        return self.memory.profile.get_profile()

    def all_facts(self):

        return self.memory.all_facts()

    def forget(self, key: str):

        return self.memory.forget(key)

    # -----------------------------
    # Free-form notes
    # -----------------------------

    def add_note(self, text: str):

        return self.memory.add_note(text)

    def notes(self):

        return self.memory.notes()

    def delete_note(self, index: int):

        return self.memory.delete_note(index)

    # -----------------------------
    # Utility
    # -----------------------------

    def stats(self):

        return self.memory.stats()

    def clear(self):

        self.memory.reset()
