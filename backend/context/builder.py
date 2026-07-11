from prompts.manager import PromptManager


class ContextBuilder:

    def __init__(self, memory):

        self.memory = memory

        self.prompts = PromptManager()

    def set_mode(self, mode):

        self.prompts.set_mode(mode)

    def build(self, user_input):

        history = self.memory.conversation.last(10)

        prompt = self.prompts.get_prompt()

        prompt += "\n\n"

        prompt += "Conversation:\n\n"

        for message in history:

            role = message["role"].capitalize()

            text = message["text"]

            prompt += f"{role}: {text}\n"

        prompt += f"\nUser: {user_input}\n"

        prompt += "\nAssistant:"

        return prompt