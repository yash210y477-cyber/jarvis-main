import json
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
    supports_tools = True

    def chat_with_tools(self, messages, tools):

        if not self.health():

            return {
                "success": False,
                "provider": self.name(),
                "error": "Gemini is not configured."
            }

        try:

            from google.generativeai import GenerativeModel

            from providers.gemini_tools import parse_response, to_contents, to_tools

            model = GenerativeModel(
                self.model.model_name,
                tools=to_tools(tools)
            )

            response = model.generate_content(
                to_contents(messages)
            )

        except Exception as error:

            return {
                "success": False,
                "provider": self.name(),
                "error": str(error)
            }

        text, calls = parse_response(response)

        assistant = {
            "role": "assistant",
            "content": text
        }

        if calls:

            assistant["tool_calls"] = [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": json.dumps(call["arguments"])
                    }
                }
                for call in calls
            ]

        return {
            "success": True,
            "provider": self.name(),
            "message": assistant,
            "tool_calls": calls,
            "content": text
        }
