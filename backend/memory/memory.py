from brain.facts import canonical_key, human_key

from memory.conversation import Conversation
from memory.profile import Profile
from memory.storage import PROFILE_FIELDS, Storage


class Memory:

    PROFILE_FIELDS = PROFILE_FIELDS

    def __init__(self, storage=None):

        self.storage = storage or Storage()

        self.profile = Profile(self.storage)

        self.conversation = Conversation(self.storage)

    # -----------------------------
    # Facts
    # -----------------------------

    def remember(self, key: str, value: str):

        key = canonical_key(key) or (key or "").strip().lower()

        value = (value or "").strip()

        if not key or not value:

            return {
                "success": False,
                "message": "Nothing to remember."
            }

        if key in self.PROFILE_FIELDS:

            return self.profile.update(key, value)

        result = self.profile.save_fact(key, value)

        result["message"] = (
            f"Got it — I'll remember your {human_key(key)} is {value}."
        )

        return result

    def recall(self, key: str):

        key = canonical_key(key) or (key or "").strip().lower()

        if not key:

            return None

        if key in self.PROFILE_FIELDS:

            profile_value = self.profile.get(key)

            if profile_value:

                return profile_value

        return self.profile.get_fact(key)

    def all_facts(self) -> list:

        return self.profile.get_facts()

    def facts(self) -> dict:

        return self.storage.facts()

    def forget(self, key: str):

        key = canonical_key(key) or (key or "").strip().lower()

        if key in self.PROFILE_FIELDS:

            return self.profile.update(key, "")

        return self.profile.delete_fact(key)

    # -----------------------------
    # Free-form notes
    # -----------------------------

    def add_note(self, text: str):

        text = (text or "").strip()

        if not text:

            return {
                "success": False,
                "message": "Nothing to remember."
            }

        notes = self.storage.add_note(text)

        return {
            "success": True,
            "message": "Got it — I'll remember that.",
            "notes": notes
        }

    def notes(self) -> list:

        return self.storage.notes()

    def delete_note(self, index: int):

        if not self.storage.delete_note(index):

            return {
                "success": False,
                "message": "Note not found."
            }

        return {
            "success": True,
            "notes": self.notes()
        }

    # -----------------------------
    # Conversation
    # -----------------------------

    def remember_conversation(self, role: str, message: str):

        self.conversation.add(role, message)

    def recent_conversation(self, limit: int = 10):

        return self.conversation.last(limit)

    def message_count(self) -> int:

        return self.conversation.count()

    def trim_conversation(self, keep: int) -> int:

        return self.conversation.trim(keep)

    # -----------------------------
    # Utility
    # -----------------------------

    def latest_summary(self):

        return self.storage.latest_summary()

    def save_summary(self, summary: str, message_count: int = 0):

        self.storage.save_summary(summary, message_count)

    def reset(self):

        self.storage.reset()

    def stats(self) -> dict:

        return {
            "profile": self.profile.get_profile(),
            "conversation_count": self.conversation.count()
        }
