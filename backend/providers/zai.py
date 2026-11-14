"""Z.ai (Zhipu GLM) through its OpenAI-compatible endpoint."""

import logging
import os

from dotenv import load_dotenv
from openai import OpenAI

from config.settings import settings
from providers.base import BaseProvider
from providers.tool_call import OpenAIToolMixin

load_dotenv()

logger = logging.getLogger(__name__)


class ZaiProvider(OpenAIToolMixin, BaseProvider):

    def __init__(self):

        self.provider_name = "zai"

        self.api_key = (os.getenv("ZAI_API_KEY") or "").strip()

        self.base_url = settings.ZAI_BASE_URL

        self.model = settings.ZAI_MODEL

        self.client = None

        self._working = None

        if self.api_key:

            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)

    def name(self) -> str:

        return self.provider_name

    def health(self) -> bool:

        return self.client is not None

    # Newest first: the account keeps whatever it can reach.
    MODELS = (
        "glm-5.3",
        "glm-4.7",
        "glm-4.6",
        "glm-4.5",
        "glm-4.5-air",
        "glm-4.5-flash",
    )

    def resolve_model(self):

        if self._working:

            return self._working

        return (self.model or self.MODELS[0]).strip()

    def _ask(self, messages, tools=None, model=None):

        """Ask every candidate model until one answers; remember the winner."""

        first = (model or self.resolve_model()).strip()

        candidates = [first] + [
            name for name in self.MODELS if name != first
        ]

        last_error = None

        for model in candidates:

            try:

                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": int(getattr(settings, "ZAI_MAX_TOKENS", 2048)),
                    "temperature": 0.6,
                }

                if tools:

                    payload["tools"] = tools

                    payload["tool_choice"] = "auto"

                reply = self.client.chat.completions.create(**payload)

                self._working = model

                return reply

            except Exception as error:

                last_error = error

                text = str(error).lower()

                # A bad key never gets better by changing models.
                if any(
                    word in text
                    for word in ("401", "unauthorized", "invalid api key", "authentication")
                ):

                    raise

                logger.info("Z.ai model %s did not answer: %s", model, error)

        raise last_error

    def chat(self, prompt: str, model: str = None) -> dict:

        if not self.health():

            return {
                "success": False,
                "provider": self.name(),
                "error": "ZAI_API_KEY is not set.",
            }

        try:

            reply = self._ask(
                [{"role": "user", "content": prompt}], model=model
            )

            return {
                "success": True,
                "provider": self.name(),
                "model": getattr(reply, "model", self.resolve_model()),
                "response": reply.choices[0].message.content,
            }

        except Exception as error:

            return {
                "success": False,
                "provider": self.name(),
                "error": str(error),
            }

    def chat_with_tools(self, messages, tools):

        if not self.health():

            return {
                "success": False,
                "provider": self.name(),
                "error": "ZAI_API_KEY is not set.",
            }

        try:

            reply = self._ask(messages, tools)

            message = reply.choices[0].message

            calls = []

            for call in getattr(message, "tool_calls", None) or []:

                import json

                try:

                    arguments = json.loads(call.function.arguments or "{}")

                except ValueError:

                    arguments = {}

                calls.append(
                    {
                        "id": getattr(call, "id", ""),
                        "name": call.function.name,
                        "arguments": arguments,
                    }
                )

            assistant = {
                "role": "assistant",
                "content": message.content or "",
            }

            if getattr(message, "tool_calls", None):

                assistant["tool_calls"] = [
                    call.model_dump() if hasattr(call, "model_dump") else call
                    for call in message.tool_calls
                ]

            return {
                "success": True,
                "provider": self.name(),
                "message": assistant,
                "tool_calls": calls,
                "content": message.content or "",
            }

        except Exception as error:

            return {
                "success": False,
                "provider": self.name(),
                "error": str(error),
            }
