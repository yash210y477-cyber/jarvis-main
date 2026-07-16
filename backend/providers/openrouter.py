import os
import requests

from providers.base import BaseProvider
from config.settings import settings


class OpenRouterProvider(BaseProvider):

    def __init__(self):

        self.provider_name = "openrouter"

        self.api_key = os.getenv("OPENROUTER_API_KEY")

        self.url = settings.OPENROUTER_URL

        self.model = settings.OPENROUTER_MODEL

        self.timeout = settings.REQUEST_TIMEOUT

    def name(self) -> str:

        return self.provider_name

    def health(self) -> bool:

        return bool(self.api_key)

    def chat(self, prompt: str) -> dict:

        if not self.health():

            return self.failure(
                "OpenRouter API key not configured."
            )

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

                timeout=self.timeout

            )

            data = response.json()

            if response.status_code != 200:

                return self.failure(data)

            return self.success(

                data["choices"][0]["message"]["content"]

            )

        except Exception as e:

            return self.failure(e)