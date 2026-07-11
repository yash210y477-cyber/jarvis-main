from brain.intent import IntentEngine
from brain.router import Router

from memory.memory import Memory

from providers.manager import AIManager

from context.builder import ContextBuilder


class Brain:

    def __init__(self):

        self.intent = IntentEngine()

        self.router = Router()

        self.memory = Memory()

        self.context = ContextBuilder(
            self.memory
        )

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

        # If router handled it
        if response.get("success"):

            message = response.get("message")

            if message:

                self.memory.conversation.add(
                    "assistant",
                    message
                )

            return response

        # -----------------------------
        # Build AI Context
        # -----------------------------

        prompt = self.context.build(
            user_input
        )

        # -----------------------------
        # AI Manager
        # -----------------------------

        ai_response = self.ai.chat(
            prompt
        )

        # -----------------------------
        # Save AI Response
        # -----------------------------

        if ai_response.get("success"):

            response_text = ai_response.get("response")

            if response_text:

                self.memory.conversation.add(
                    "assistant",
                    response_text
                )

        return ai_response
    
    def set_mode(self, mode):
        
        self.context.set_mode(mode)
        
        return {
            
            "success": True,
           
            "mode": mode
            
            }