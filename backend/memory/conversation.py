from memory.storage import Storage


class Conversation:

    def __init__(self):

        self.storage = Storage()

    def add(self, role: str, text: str):

        data = self.storage.read()

        data["conversation"].append(
            {
                "role": role,
                "text": text
            }
        )

        self.storage.write(data)

    def get(self):

        data = self.storage.read()

        return data["conversation"]

    def last(self, limit=10):

        data = self.storage.read()

        return data["conversation"][-limit:]

    def clear(self):

        data = self.storage.read()

        data["conversation"] = []

        self.storage.write(data)

        return {
            "success": True,
            "message": "Conversation cleared."
        }

    def count(self):

        data = self.storage.read()

        return len(data["conversation"])