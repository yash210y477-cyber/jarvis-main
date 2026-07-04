from brain.intent import IntentEngine
from brain.router import Router

from memory.memory import Memory

from providers.gemini import GeminiProvider


class Brain:

    def __init__(self):

        self.intent = IntentEngine()

        self.router = Router()

        self.memory = Memory()

        self.ai = GeminiProvider()

    def process(self, user_input: str):

        # Save user message
        self.memory.conversation.add(
            "user",
            user_input
        )

        command = self.intent.detect(
            user_input
        )

        response = self.router.route(
            command
        )

        # Router handled the request
        if response.get("success"):

            message = response.get("message")

            if message:

                self.memory.conversation.add(
                    "assistant",
                    message
                )

            return response

        # Send to AI
        ai_response = self.ai.chat(
            user_input
        )

        if ai_response.get("success"):

            self.memory.conversation.add(
                "assistant",
                ai_response["response"]
            )

        return ai_response