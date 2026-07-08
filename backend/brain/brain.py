from brain.intent import IntentEngine
from brain.router import Router

from memory.memory import Memory

from providers.gemini import GeminiProvider
from providers.ollama import OllamaProvider


class Brain:

    def __init__(self):

        self.intent = IntentEngine()

        self.router = Router()

        self.memory = Memory()

        self.ai = GeminiProvider()

        self.local_ai = OllamaProvider()

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

        # Router handled the request

        if response.get("success"):

            message = response.get("message")

            if message:

                self.memory.conversation.add(
                    "assistant",
                    message
                )

            return response

        # -----------------------------
        # Gemini AI
        # -----------------------------

        ai_response = self.ai.chat(
            user_input
        )

        if ai_response.get("success"):

            self.memory.conversation.add(
                "assistant",
                ai_response["response"]
            )

            return ai_response

        print("Gemini failed. Switching to Ollama...")

        # -----------------------------
        # Ollama Fallback
        # -----------------------------

        ollama_response = self.local_ai.chat(
            user_input
        )

        if ollama_response.get("success"):

            self.memory.conversation.add(
                "assistant",
                ollama_response["response"]
            )

            return ollama_response

        # -----------------------------
        # Both Failed
        # -----------------------------

        return {

            "success": False,

            "provider": "brain",

            "message": "Unable to generate response.",

            "gemini_error": ai_response.get("error"),

            "ollama_error": ollama_response.get("error")

        }