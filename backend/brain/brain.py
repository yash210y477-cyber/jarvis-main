from providers.manager import AIManager

from brain.intent import IntentEngine
from brain.router import Router

from memory.manager import MemoryManager
from memory.context import ContextBuilder


class Brain:

    def __init__(self):

        self.ai = AIManager()

        self.intent = IntentEngine()

        self.router = Router()

        self.memory = MemoryManager()

        self.context = ContextBuilder(self.memory)

    def chat(self, message: str):

        # Save user message
        self.memory.add_user_message(message)

        # Detect intent
        command = self.intent.detect(message)

        # Try router first
        result = self.router.route(command)

        if result.get("success"):

            reply = (
                result.get("message")
                or result.get("response")
                or str(result)
            )

            self.memory.add_assistant_message(reply)

            return {
                "success": True,
                "provider": "router",
                "response": reply,
                "data": result
            }

        # Fallback to AI
        prompt = self.context.build(message)

        ai_response = self.ai.chat(prompt)

        if ai_response.get("success"):

            self.memory.add_assistant_message(
                ai_response["response"]
            )

        return ai_response

    def clear_memory(self):

        self.memory.clear()