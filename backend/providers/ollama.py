"""Local Ollama provider.

Runs a model on this computer through Ollama (http://127.0.0.1:11434), so
JARVIS still answers when every cloud API key is missing, rejected or out of
credit. It is listed last in the provider priority for exactly that reason.
"""

import json
import logging
import time
import urllib.request

from openai import OpenAI

from config.settings import settings
from providers.base import BaseProvider
from providers.tool_call import OpenAIToolMixin


logger = logging.getLogger(__name__)


HEALTH_TTL_SECONDS = 15.0


class OllamaProvider(OpenAIToolMixin, BaseProvider):

    def __init__(self):

        self.provider_name = "ollama"

        self.base_url = (
            settings.OLLAMA_BASE_URL or "http://127.0.0.1:11434"
        ).rstrip("/")

        self.model = settings.OLLAMA_MODEL or ""

        self.client = None

        self._models = []
        self._alive = False
        self._checked_at = 0.0

        self._refresh()

    # ------------------------------------------------------------ endpoints

    def _root(self) -> str:

        return (
            self.base_url[:-3]
            if self.base_url.endswith("/v1")
            else self.base_url
        )

    def _api(self, path: str) -> str:

        return f"{self._root()}{path}"

    def installed_models(self) -> list:

        try:

            with urllib.request.urlopen(
                self._api("/api/tags"), timeout=2.0
            ) as response:

                payload = json.loads(response.read().decode("utf-8"))

        except Exception:

            return []

        return [
            item.get("name")
            for item in payload.get("models") or []
            if item.get("name")
        ]

    def _refresh(self) -> bool:

        models = self.installed_models()

        self._models = models
        self._alive = bool(models)
        self._checked_at = time.monotonic()

        if not models:

            self.client = None

            return False

        if not self.model or self.model not in models:

            # Prefer a small general chat model when the configured one is gone.
            preferred = [name for name in models if "qwen" in name] or models

            self.model = preferred[0]

        self.client = OpenAI(
            base_url=self._api("/v1"),
            api_key="ollama",
            timeout=float(settings.OLLAMA_TIMEOUT),
            max_retries=0,
        )

        return True

    # -------------------------------------------------------------- provider

    def name(self) -> str:

        return self.provider_name

    def health(self) -> bool:

        if time.monotonic() - self._checked_at > HEALTH_TTL_SECONDS:

            self._refresh()

        return bool(self._alive and self.client is not None)

    def _system(self) -> str:
        """Instructions a small local model needs spelled out."""

        from brain import language as reply_language

        mode = reply_language.current()

        if mode == "english":

            style = "Answer in English."

        elif mode == "hinglish":

            style = (
                "Answer in Hinglish: Hindi and English mixed in Roman script, "
                "the way friends talk in India."
            )

        else:

            style = (
                "Answer in the language the user wrote in: English for English, "
                "Hinglish for Hinglish."
            )

        return (
            "You are JARVIS, a friendly assistant running on this Windows PC. "
            f"{style} Keep answers to one or two short sentences and be "
            "practical: the user gives short spoken commands."
        )

    @staticmethod
    def _trim(prompt: str) -> str:
        """Keep the instructions at the top and the newest turns at the end."""

        prompt = (prompt or "").strip()

        limit = int(settings.OLLAMA_PROMPT_CHARS)

        if limit <= 0 or len(prompt) <= limit:

            return prompt

        head = prompt[:400]

        tail = prompt[-(limit - len(head)):]

        return head + "\n...\n" + tail

    SKIP = ("embed",)

    def free_models(self, first=None) -> list:
        """The local models to try, the configured one first."""

        names = [first, self.model, *self._models]

        return [
            name
            for name in dict.fromkeys(name for name in names if name)
            if not any(skip in name for skip in self.SKIP)
        ] or [self.model]

    def chat(self, prompt: str) -> dict:

        if not self.health():

            return {
                "success": False,
                "provider": self.name(),
                "error": (
                    "Ollama is not running (start it with `ollama serve`, "
                    f"expected at {self._root()})."
                ),
            }

        prompt = self._trim(prompt)

        last_error = None

        for name in self.free_models():

            try:

                response = self.client.chat.completions.create(
                    model=name,
                    messages=[
                        {"role": "system", "content": self._system()},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=int(settings.OLLAMA_MAX_TOKENS),
                    temperature=0.4,
                )

                return {
                    "success": True,
                    "provider": self.name(),
                    "model": name,
                    "response": response.choices[0].message.content,
                }

            except Exception as error:

                last_error = error

                logger.info("Ollama model %s did not answer: %s", name, error)

        return {
            "success": False,
            "provider": self.name(),
            "error": str(last_error),
        }
