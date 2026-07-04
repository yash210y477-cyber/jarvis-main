from brain.intent import IntentEngine
from brain.router import Router

from providers.gemini import GeminiProvider


class Brain:

    def __init__(self):

        self.intent_engine = IntentEngine()

        self.router = Router()

        self.ai = GeminiProvider()

    def process(self, user_input: str):

        command = self.intent_engine.detect(user_input)

        print(command)

        response = self.router.route(command)

        if response.get("success"):

            if response.get("action"):

                return response

        return self.ai.chat(user_input)