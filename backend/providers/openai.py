import os

from openai import OpenAI
from dotenv import load_dotenv

from providers.base import BaseProvider
from providers.tool_call import OpenAIToolMixin
from config.settings import settings

load_dotenv()


class OpenAIProvider(OpenAIToolMixin, BaseProvider):

    def __init__(self):

        self.provider_name = "openai"

        self.api_key = os.getenv("OPENAI_API_KEY")

        self.model = settings.OPENAI_MODEL

        self.client = None

        if self.api_key:

            self.client = OpenAI(
                api_key=self.api_key
            )

    def name(self) -> str:

        return self.provider_name

    def health(self) -> bool:

        return self.client is not None

    def chat(self, prompt: str) -> dict:

        if not self.health():

            return {

                "success": False,

                "provider": self.name(),

                "error": "OpenAI API key not configured."

            }

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

            return {

                "success": True,

                "provider": self.name(),

                "response": response.choices[0].message.content

            }

        except Exception as e:

            return {

                "success": False,

                "provider": self.name(),

                "error": str(e)

            }