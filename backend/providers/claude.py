import os

from anthropic import Anthropic
from dotenv import load_dotenv

from providers.base import BaseProvider
from config.settings import settings

load_dotenv()


class ClaudeProvider(BaseProvider):

    def __init__(self):

        self.provider_name = "claude"

        self.api_key = os.getenv("CLAUDE_API_KEY")

        self.model = "claude-sonnet-4-20250514"

        self.client = None

        if self.api_key:

            self.client = Anthropic(
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

                "error": "Claude API key not configured."

            }

        try:

            response = self.client.messages.create(

                model=self.model,

                max_tokens=1024,

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

                "response": response.content[0].text

            }

        except Exception as e:

            return {

                "success": False,

                "provider": self.name(),

                "error": str(e)

            }