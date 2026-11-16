import logging
import os

from groq import Groq
from dotenv import load_dotenv

from providers.base import BaseProvider
from providers import ranking
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

    def chat(self, prompt: str, model: str = None) -> dict:

        if not self.health():

            return {

                "success": False,

                "provider": self.name(),

                "error": "Groq API key not configured."

            }

        try:

            last_error = None

            for name in self.free_models(model):

                try:

                    response = self.client.chat.completions.create(

                        model=name,

                        messages=[{"role": "user", "content": prompt}],

                        max_tokens=int(getattr(settings, "GROQ_MAX_TOKENS", 2048)),

                        temperature=0.6,

                    )

                    return {

                        "success": True,

                        "provider": self.name(),

                        "model": getattr(response, "model", name) or name,

                        "response": response.choices[0].message.content

                    }

                except Exception as error:

                    last_error = error

                    text = str(error).lower()

                    # A bad key never gets better by changing models.
                    if any(
                        word in text
                        for word in (
                            "401", "unauthorized", "invalid api key", "authentication"
                        )
                    ):

                        break

                    logger.info("Groq model %s did not answer: %s", name, error)

            return {

                "success": False,

                "provider": self.name(),

                "error": str(last_error)

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

    def free_models(self, first=None):
        """The free chat models this account can reach, best first."""

        available = self.known_models()

        ranked = [name for provider, name in ranking.models("text") if provider == "groq"]

        wanted = [first, *ranked, self.model, self.fallback_model, *self.PREFERENCE]

        chain = []

        for name in wanted:

            if not name or name in chain or any(skip in name for skip in self.SKIP):

                continue

            # Groq accounts differ in what they can reach.
            if available and name not in available:

                continue

            chain.append(name)

        if chain:

            return chain

        # Nothing preferred is reachable: any chat model on the account.
        return [
            name for name in sorted(available) if not any(s in name for s in self.SKIP)
        ][:1] or [self.model]

    def resolve_model(self):
        """A model id this account can actually answer with."""

        return (self.free_models() or [self.model])[0]

