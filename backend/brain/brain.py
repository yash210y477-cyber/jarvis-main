from brain.intent import IntentEngine
from brain.router import Router

from memory.memory import Memory

from providers.manager import AIManager


class Brain:

    def __init__(self):

        self.intent = IntentEngine()

        self.router = Router()

        self.memory = Memory()

        self.ai = AIManager()

    def process(self, user_input: str):

        # -----------------------------
        # Save User Message
        # -----------------------------

        self.memory.conversation.add(
            "user",
            user_input
        )

        # -----------------------------
        # Detect Intent
        # -----------------------------

        command = self.intent.detect(
            user_input
        )

        # -----------------------------
        # Router
        # -----------------------------

        response = self.router.route(
            command
        )

        if response.get("success"):

            message = response.get("message")

            if message:

                self.memory.conversation.add(
                    "assistant",
                    message
                )

            return response

        # -----------------------------
        # AI Manager
        # -----------------------------

        ai_response = self.ai.chat(
            user_input
        )

        if ai_response.get("success"):

            if ai_response.get("response"):

                self.memory.conversation.add(
                    "assistant",
                    ai_response["response"]
                )

        return ai_response