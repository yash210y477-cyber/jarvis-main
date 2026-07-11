from providers.gemini import GeminiProvider
from providers.openrouter import OpenRouterProvider


class AIManager:

    def __init__(self):

        self.providers = [

            GeminiProvider(),

            OpenRouterProvider()

        ]

    def chat(self, prompt: str):

        errors = []

        for provider in self.providers:

            result = provider.chat(prompt)

            if result.get("success"):

                return result

            errors.append({

                "provider": provider.name(),

                "error": result.get("error")

            })

        return {

            "success": False,

            "provider": "manager",

            "message": "All AI providers failed.",

            "errors": errors

        }