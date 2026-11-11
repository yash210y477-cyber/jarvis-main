from memory.storage import Storage


class Conversation:

    def __init__(self, storage=None):

        self.storage = storage or Storage()

    def add(self, role: str, text: str):

        return self.storage.add_message(role, text)

    def get(self) -> list:

        return self.storage.messages()

    def last(self, limit=10) -> list:

        return self.storage.messages(limit=limit)

    def clear(self):

        self.storage.clear_messages()

        return {
            "success": True,
            "message": "Conversation cleared."
        }

    def count(self) -> int:

        return self.storage.message_count()

    def trim(self, keep: int) -> int:

        return self.storage.trim_messages(keep)
