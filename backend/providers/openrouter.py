import os
import requests

from dotenv import load_dotenv

from providers.base import BaseProvider


load_dotenv()


class OpenRouterProvider(BaseProvider):

    def __init__(self):

        self.provider_name = "openrouter"

        self.api_key = os.getenv("OPENROUTER_API_KEY")

        self.url = "https://openrouter.ai/api/v1/chat/completions"

        self.model = "openrouter/auto"

    def name(self) -> str:

        return self.provider_name

    def health(self) -> bool:

        return bool(self.api_key)

    def chat(self, prompt: str) -> dict:

        if not self.health():

            return {

                "success": False,

                "provider": self.name(),

                "error": "OpenRouter API key not configured."

            }

        try:

            headers = {

                "Authorization": f"Bearer {self.api_key}",

                "Content-Type": "application/json",

                "HTTP-Referer": "http://localhost:8000",

                "X-Title": "Jarvis"

            }

            payload = {

                "model": self.model,

                "messages": [

                    {

                        "role": "user",

                        "content": prompt

                    }

                ]

            }

            response = requests.post(

                self.url,

                headers=headers,

                json=payload,

                timeout=60

            )

            data = response.json()

            if response.status_code != 200:

                return {

                    "success": False,

                    "provider": self.name(),

                    "error": data

                }

            return {

                "success": True,

                "provider": self.name(),

                "response": data["choices"][0]["message"]["content"]

            }

        except Exception as e:

            return {

                "success": False,

                "provider": self.name(),

                "error": str(e)

            }