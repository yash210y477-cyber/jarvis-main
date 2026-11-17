from memory.manager import MemoryManager
from memory.semantic import search_memory
from brain.summary_manager import SummaryManager


LANGUAGE_RULES = {

    "hinglish": (
        "Reply in Hinglish (Hindi + English mixed, Roman script), short and "
        "friendly. Example: \"Ho gaya, calculator khol diya.\" Keep command "
        "names, file names and code in English."
    ),

    "english": "Reply in English.",

    "hindi": "Reply in Hindi (Devanagari script).",
}


class ContextBuilder:

    RECENT_MESSAGES = 6

    NOISE = ("all ai provider failed", "no ai provider", "ai provider timed out")

    MESSAGE_CHARS = 400

    def __init__(self, memory: MemoryManager):

        self.memory = memory
        self.summary = SummaryManager()

    def build(self, current_message: str):

        prompt = []

        # -------------------------
        # Reply Language
        # -------------------------

        from brain import language

        rule = LANGUAGE_RULES.get(
            language.reply_language(current_message), LANGUAGE_RULES["english"]
        )

        prompt.append("### Reply Language")
        prompt.append(rule)
        prompt.append("")

        # -------------------------
        # Conversation Summary
        # -------------------------

        summary = self.summary.latest()

        if summary:

            prompt.append("### Conversation Summary")
            prompt.append(summary)
            prompt.append("")

        # -------------------------
        # User Profile
        # -------------------------

        profile = self.memory.memory.profile.get_profile()

        if profile:

            prompt.append("### User Profile")

            for key, value in profile.items():

                if value:

                    prompt.append(f"{key}: {value}")

            prompt.append("")

        # -------------------------
        # Relevant Memory (semantic search)
        # -------------------------

        needle = " ".join((current_message or "").lower().split())

        relevant = [
            item for item in search_memory(current_message)
            if " ".join(item["text"].lower().split()) != needle
        ]

        if relevant:

            prompt.append("### Relevant Memory (semantic search)")

            for item in relevant:

                prompt.append(f"- {item['text']}")

            prompt.append("")

        # -------------------------
        # Recent Conversation
        # -------------------------

        recent = [
            item for item in self.memory.get_messages()
            if not any(word in (item["text"] or "").lower() for word in self.NOISE)
        ]

        if recent:

            prompt.append("### Recent Conversation")

            for item in recent[-self.RECENT_MESSAGES:]:

                role = item["role"].capitalize()

                text = (item["text"] or "").strip()

                if len(text) > self.MESSAGE_CHARS:

                    text = text[: self.MESSAGE_CHARS] + "..."

                prompt.append(f"{role}: {text}")

            prompt.append("")

        # -------------------------
        # Current Message
        # -------------------------

        prompt.append("### Current User Message")
        prompt.append(current_message)

        return "\n".join(prompt)