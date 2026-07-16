import os

from groq import Groq

from providers.base import BaseProvider
from config.settings import settings


class GroqProvider(BaseProvider):

    def __init__(self):

        self.provider_name = "groq"

        self.api_key = os.getenv("GROQ_API_KEY")

        self.model = settings.GROQ_MODEL

        self.client = None

        if self.api_key:

            self.client = Groq(
                api_key=self.api_key
            )

    def name(self) -> str:

        return self.provider_name

    def health(self) -> bool:

        return self.client is not None

    def chat(self, prompt: str) -> dict:

        if not self.health():

            return self.failure(
                "Groq API key not configured."
            )

        try:

            response = self.client.chat.completions.create(

                model=self.model,

                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]

            )

            return self.success(

                response.choices[0].message.content

            )

        except Exception as e:

            return self.failure(e)