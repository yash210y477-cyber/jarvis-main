from brain.facts import canonical_key, human_key

from memory.profile import Profile
from memory.conversation import Conversation


class Memory:

    PROFILE_FIELDS = ("name", "email", "city", "occupation")

    def __init__(self):

        self.profile = Profile()

        self.conversation = Conversation()

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

    def all_facts(self):

        return self.profile.get_facts()

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

        notes = list(self.notes())

        notes.append(text)

        self.profile.storage.write(
            self._with_notes(notes)
        )

        return {
            "success": True,
            "message": "Got it — I'll remember that.",
            "notes": notes
        }

    def notes(self):

        data = self.profile.storage.read()

        return data.get("notes", [])

    def delete_note(self, index: int):

        notes = list(self.notes())

        if 0 <= index < len(notes):

            notes.pop(index)

            self.profile.storage.write(
                self._with_notes(notes)
            )

            return {
                "success": True,
                "notes": notes
            }

        return {
            "success": False,
            "message": "Note not found."
        }

    def _with_notes(self, notes):

        data = self.profile.storage.read()

        data["notes"] = notes

        return data

    # -----------------------------
    # Conversation
    # -----------------------------

    def remember_conversation(
        self,
        role: str,
        message: str
    ):

        self.conversation.add(
            role,
            message
        )

    def recent_conversation(
        self,
        limit: int = 10
    ):

        return self.conversation.last(
            limit
        )

    def reset(self):

        self.profile.clear()

        self.conversation.clear()

    def stats(self):

        return {
            "profile": self.profile.get_profile(),
            "conversation_count": self.conversation.count()
        }
