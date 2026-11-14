import logging
import os

from groq import Groq
from dotenv import load_dotenv

from providers.base import BaseProvider
from providers.tool_call import OpenAIToolMixin
from config.settings import settings

load_dotenv()

logger = logging.getLogger(__name__)


class GroqProvider(OpenAIToolMixin, BaseProvider):

    def __init__(self):

        self.provider_name = "groq"

        self.api_key = os.getenv("GROQ_API_KEY")

        self.model = settings.GROQ_MODEL

        self.fallback_model = settings.GROQ_FALLBACK_MODEL

        self._known = None

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

            return {

                "success": False,

                "provider": self.name(),

                "error": "Groq API key not configured."

            }

        try:

            response = self._complete(prompt, self.resolve_model())

            return {

                "success": True,

                "provider": self.name(),

                "model": getattr(response, "model", self.model),

                "response": response.choices[0].message.content

            }

        except Exception as e:

            return {

                "success": False,

                "provider": self.name(),

                "error": str(e)

            }

    # Groq accounts differ in what they can reach, so the id is resolved
    # against the account's own list before the first answer.
    PREFERENCE = (
        "minimaxai/minimax-m2.7",
        "minimaxai/minimax-m2",
        "openai/gpt-oss-120b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-20b",
        "llama-3.3-70b-versatile",
    )

    def known_models(self):

        if self._known is None:

            try:

                self._known = {
                    model.id for model in self.client.models.list().data
                }

            except Exception as error:

                logger.warning("Groq model list unavailable: %s", error)

                self._known = set()

        return self._known

    SKIP = ("whisper", "orpheus", "prompt-guard", "tts")

    def resolve_model(self):
        """A model id this account can actually answer with."""

        available = self.known_models()

        for name in (self.model, self.fallback_model, *self.PREFERENCE):

            if name and (not available or name in available):

                return name

        # Nothing preferred is reachable: take any chat model on the account.
        for name in sorted(available):

            if not any(skip in name for skip in self.SKIP):

                return name

        return self.model

    def _complete(self, prompt: str, model: str):
        """One answer from Groq, retried on the fallback model if needed."""

        try:

            return self.client.chat.completions.create(

                model=model,

                messages=[{"role": "user", "content": prompt}],

                max_tokens=int(getattr(settings, "GROQ_MAX_TOKENS", 2048)),

                temperature=0.6,

            )

        except Exception as error:

            # A retired model id answers 400/404; the fallback still replies.
            text = str(error).lower()

            gone = any(
                word in text
                for word in ("model", "not found", "decommission", "does not exist")
            )

            if (
                model != self.fallback_model
                and gone
                and self.fallback_model
            ):

                return self.client.chat.completions.create(

                    model=self.fallback_model,

                    messages=[{"role": "user", "content": prompt}],

                    max_tokens=int(getattr(settings, "GROQ_MAX_TOKENS", 2048)),

                    temperature=0.6,

                )

            raise
