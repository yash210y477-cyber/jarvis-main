from providers.manager import AIManager

from brain.intent import IntentEngine
from brain.router import Router
from brain.summary_manager import SummaryManager

from memory.manager import MemoryManager
from memory.context import ContextBuilder




class Brain:

    SUMMARY_THRESHOLD = 50

    def __init__(self):

        self.ai = AIManager()

        self.intent = IntentEngine()

        self.router = Router()

        self.memory = MemoryManager()

        self.context = ContextBuilder(self.memory)

        self.summary = SummaryManager()

    def _check_summary(self):

        conversation = self.memory.get_messages()

        if len(conversation) >= self.SUMMARY_THRESHOLD:

            self.summary.generate(conversation)

            self.memory.clear_messages()

    def chat(self, message: str):

        # -------------------------
        # Save User Message
        # -------------------------

        self.memory.add_user_message(message)

        # -------------------------
        # Detect Intent
        # -------------------------

        command = self.intent.detect(message)

        # -------------------------
        # Execute Router
        # -------------------------

        result = self.router.route(command)

        if result.get("success"):

            reply = (
                result.get("message")
                or result.get("response")
                or str(result)
            )

            self.memory.add_assistant_message(reply)

            self._check_summary()

            return {

                "success": True,

                "provider": "router",

                "response": reply,

                "data": result

            }

        # -------------------------
        # Build AI Context
        # -------------------------

        prompt = self.context.build(message)

        # -------------------------
        # Ask AI
        # -------------------------

        ai_response = self.ai.chat(prompt)

        if ai_response.get("success"):

            self.memory.add_assistant_message(

                ai_response["response"]

            )

        self._check_summary()

        return ai_response

    def clear_memory(self):

        self.memory.clear()