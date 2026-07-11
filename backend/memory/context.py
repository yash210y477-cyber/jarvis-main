from memory.manager import MemoryManager


class ContextBuilder:

    def __init__(self, memory: MemoryManager):

        self.memory = memory

    def build(self, current_message: str):

        profile = self.memory.memory.profile.get_profile()

        conversation = self.memory.get_messages()

        prompt = []

        if profile["name"]:

            prompt.append(

                f"User Name: {profile['name']}"

            )

        if conversation:

            prompt.append("Conversation History:")

            for item in conversation:

                prompt.append(

                    f"{item['role'].capitalize()}: {item['text']}"

                )

        prompt.append("Current User Message:")

        prompt.append(current_message)

        return "\n".join(prompt)    