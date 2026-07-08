class ContextBuilder:

    def __init__(self, memory):

        self.memory = memory

    def build(self, user_input: str):

        history = self.memory.conversation.last(10)

        prompt = ""

        prompt += (
            "You are JARVIS, an intelligent AI assistant.\n\n"
        )

        for message in history:

            role = message["role"].capitalize()

            text = message["text"]

            prompt += f"{role}: {text}\n"

        prompt += f"\nUser: {user_input}\n"

        prompt += "Assistant:"

        return prompt 