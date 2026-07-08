from providers.gemini import GeminiProvider
from providers.ollama import OllamaProvider


class AIManager:

    def __init__(self):

        self.gemini = GeminiProvider()
        self.ollama = OllamaProvider()

    def chat(self, prompt: str):

        # -----------------------------
        # Try Gemini
        # -----------------------------

        gemini_response = self.gemini.chat(prompt)

        if gemini_response.get("success"):
            return gemini_response

        print(f"Gemini unavailable: {gemini_response.get('error')}")
        print("Switching to Ollama...")

        # -----------------------------
        # Try Ollama
        # -----------------------------

        ollama_response = self.ollama.chat(prompt)

        if ollama_response.get("success"):
            return ollama_response

        # -----------------------------
        # Both Failed
        # -----------------------------

        return {

            "success": False,

            "provider": "manager",

            "message": "Unable to generate response.",

            "gemini_error": gemini_response.get("error"),

            "ollama_error": ollama_response.get("error")

        }