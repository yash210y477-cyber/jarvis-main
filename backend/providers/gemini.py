import os

import google.generativeai as genai

from dotenv import load_dotenv

load_dotenv()


class GeminiProvider:

    def __init__(self):

        api_key = os.getenv("GEMINI_API_KEY")

        self.model = None

        if api_key:

            genai.configure(api_key=api_key)

            self.model = genai.GenerativeModel(
                "gemini-2.5-flash"
            )

    def chat(self, prompt: str):

        if self.model is None:

            return {

                "success": False,

                "provider": "gemini",

                "error": "Gemini API key not configured."

            }

        try:

            response = self.model.generate_content(prompt)

            return {

                "success": True,

                "provider": "gemini",

                "response": response.text

            }

        except Exception as e:

            return {

                "success": False,

                "provider": "gemini",

                "error": str(e)

            }