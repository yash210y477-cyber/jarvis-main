import os

from openai import OpenAI

from providers.base import BaseProvider
from config.settings import settings


class DeepSeekProvider(BaseProvider):

    def __init__(self):

        self.provider_name = "deepseek"

        self.api_key = os.getenv("DEEPSEEK_API_KEY")

        self.model = settings.DEEPSEEK_MODEL

        self.client = None

        if self.api_key:

            self.client = OpenAI(

                api_key=self.api_key,

                base_url="https://api.deepseek.com"

            )

    def name(self) -> str:

        return self.provider_name

    def health(self) -> bool:

        return self.client is not None

    def chat(self, prompt: str) -> dict:

        if not self.health():

            return self.failure(
                "DeepSeek API key not configured."
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