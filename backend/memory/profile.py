from memory.storage import PROFILE_FIELDS, Storage


class Profile:

    def __init__(self, storage=None):

        self.storage = storage or Storage()

        self.profile_fields = set(PROFILE_FIELDS)

    def get_profile(self) -> dict:

        return self.storage.get_profile()

    def get(self, key: str):

        value = self.storage.get_profile().get(key)

        return value or None

    def update(self, key: str, value: str):

        if key not in self.profile_fields:

            return {
                "success": False,
                "message": f"Invalid profile field: {key}"
            }

        value = (value or "").strip()

        self.storage.set_profile(key, value)

        if not value:

            return {
                "success": True,
                "message": f"Forgot your {key}."
            }

        return {
            "success": True,
            "message": f"Got it — I'll remember your {key} is {value}."
        }

    def save_fact(self, key: str, value: str):

        value = (value or "").strip()

        if not key or not value:

            return {
                "success": False,
                "message": "Nothing to remember."
            }

        self.storage.set_fact(key, value)

        return {
            "success": True,
            "message": f"Got it — I'll remember your {key} is {value}."
        }

    def get_fact(self, key: str):

        return self.storage.get_fact(key)

    def get_facts(self) -> list:

        return [
            {"key": key, "value": value}
            for key, value in self.storage.facts().items()
        ]

    def delete_fact(self, key: str):

        if not self.storage.delete_fact(key):

            return {
                "success": False,
                "message": f"I don't have anything saved for {key}."
            }

        return {
            "success": True,
            "message": f"Forgot your {key.replace('_', ' ')}."
        }

    def clear(self):

        self.storage.clear_profile()

        self.storage.clear_facts()
