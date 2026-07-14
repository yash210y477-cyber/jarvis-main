import os
import google.generativeai as genai

from dotenv import load_dotenv

from providers.base import BaseProvider
from config.settings import settings

load_dotenv()


class GeminiProvider(BaseProvider):

    def __init__(self):

        self.provider_name = "gemini"

        self.model = None

        self.api_key = os.getenv("GEMINI_API_KEY")

        if self.api_key:

            try:

                genai.configure(
                    api_key=self.api_key
                )

                self.model = genai.GenerativeModel(
                    settings.GEMINI_MODEL
                )

            except Exception:

                self.model = None

    def name(self) -> str:

        return self.provider_name

    def health(self) -> bool:

        return self.model is not None

    def chat(self, prompt: str) -> dict:

        if not self.health():

            return {
                "success": False,
                "provider": self.name(),
                "error": "Gemini is not configured."
            }

        try:

            response = self.model.generate_content(
                prompt
            )

            text = ""

            if hasattr(response, "text"):

                text = response.text

            return {
                "success": True,
                "provider": self.name(),
                "response": text
            }

        except Exception as e:

            return {
                "success": False,
                "provider": self.name(),
                "error": str(e)
            }