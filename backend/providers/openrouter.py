import json
import os

import requests

from dotenv import load_dotenv

from providers.base import BaseProvider
from config.settings import settings


load_dotenv()


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

                "max_tokens": max(64, int(getattr(settings, "OPENROUTER_MAX_TOKENS", 512))),

                "max_tokens": max(64, int(getattr(settings, "OPENROUTER_MAX_TOKENS", 512))),

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
    supports_tools = True

    def chat_with_tools(self, messages, tools):

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
                "max_tokens": max(64, int(getattr(settings, "OPENROUTER_MAX_TOKENS", 512))),
                "messages": messages,
                "tools": tools,
                "tool_choice": "auto"
            }

            response = requests.post(
                self.url,
                headers=headers,
                json=payload,
                timeout=self.timeout
            )

            data = response.json()

            if response.status_code != 200:

                return {
                    "success": False,
                    "provider": self.name(),
                    "error": data
                }

            raw = data["choices"][0]["message"]

            calls = []

            for call in raw.get("tool_calls") or []:

                function = call.get("function") or {}

                try:

                    arguments = json.loads(function.get("arguments") or "{}")

                except (TypeError, ValueError):

                    arguments = {}

                calls.append({
                    "id": call.get("id") or "",
                    "name": function.get("name"),
                    "arguments": arguments
                })

            assistant = {
                "role": "assistant",
                "content": raw.get("content") or ""
            }

            if raw.get("tool_calls"):

                assistant["tool_calls"] = raw["tool_calls"]

            return {
                "success": True,
                "provider": self.name(),
                "message": assistant,
                "tool_calls": calls,
                "content": raw.get("content") or ""
            }

        except Exception as error:

            return {
                "success": False,
                "provider": self.name(),
                "error": str(error)
            }
