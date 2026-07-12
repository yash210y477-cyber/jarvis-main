from memory.manager import MemoryManager
from brain.summary_manager import SummaryManager


class ContextBuilder:

    RECENT_MESSAGES = 10

    def __init__(self, memory: MemoryManager):

        self.memory = memory
        self.summary = SummaryManager()

    def build(self, current_message: str):

        prompt = []

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
        # Recent Conversation
        # -------------------------

        recent = self.memory.get_messages()

        if recent:

            prompt.append("### Recent Conversation")

            for item in recent[-self.RECENT_MESSAGES:]:

                role = item["role"].capitalize()

                prompt.append(

                    f"{role}: {item['text']}"

                )

            prompt.append("")

        # -------------------------
        # Current Message
        # -------------------------

        prompt.append("### Current User Message")
        prompt.append(current_message)

        return "\n".join(prompt)