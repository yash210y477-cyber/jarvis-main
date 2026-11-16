"""Z.ai (Zhipu GLM) through its OpenAI-compatible endpoint."""

import base64
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config.settings import settings
from providers.base import BaseProvider
from providers.tool_call import OpenAIToolMixin

load_dotenv()

logger = logging.getLogger(__name__)

# z.ai answers 429 "Insufficient balance or no resource package" whenever the
# account is out of credit. That does not fix itself between two messages, so
# instead of buying five failed calls per reply the paid models step aside for
# a while and the free one answers at once.
BALANCE_COOLDOWN = 1800

FREE_MODELS = ("glm-4.5-flash",)

_paid_down_until = 0.0


def _is_balance_error(error) -> bool:

    text = str(error).lower()

    return any(
        word in text
        for word in (
            "1113",
            "insufficient balance",
            "no resource package",
            "please recharge",
        )
    )


def _state_file():
    """The empty-wallet note survives a restart, so it is not re-probed."""

    from memory.storage import data_dir

    return data_dir() / "zai_balance.txt"


def _paid_down() -> bool:

    global _paid_down_until

    if not _paid_down_until:

        try:

            _paid_down_until = float(_state_file().read_text(encoding="utf-8").strip() or 0)

        except (OSError, ValueError):

            _paid_down_until = 0.0

    return time.time() < _paid_down_until


def _mark_paid_down() -> None:

    global _paid_down_until

    _paid_down_until = time.time() + BALANCE_COOLDOWN

    try:

        _state_file().write_text(str(_paid_down_until), encoding="utf-8")

    except OSError:

        pass

    logger.info("z.ai has no balance; paid models off for %s min", BALANCE_COOLDOWN // 60)


def paid_down() -> bool:
    """True while the empty wallet keeps the paid models out of the way."""

    return _paid_down()


def reset_balance_cooldown() -> None:
    """Forget an empty wallet (used after a recharge or by tests)."""

    global _paid_down_until

    _paid_down_until = 0.0

    try:

        _state_file().unlink()

    except OSError:

        pass


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

        # The free model answers while the wallet is empty; once the cooldown
        # is over the configured (better) model gets its chance again.
        if self._working and (_paid_down() or self._working not in FREE_MODELS):

            return self._working

        return (self.model or self.MODELS[0]).strip()

    def _ask(self, messages, tools=None, model=None):

        """Ask every candidate model until one answers; remember the winner."""

        first = (model or self.resolve_model()).strip()

        candidates = [first] + [
            name for name in self.MODELS if name != first
        ]

        if _paid_down():

            # Only the free model can answer while the wallet is empty.
            candidates = [name for name in candidates if name in FREE_MODELS]

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

                if _is_balance_error(error):

                    _mark_paid_down()

                text = str(error).lower()

                # A bad key never gets better by changing models.
                if any(
                    word in text
                    for word in ("401", "unauthorized", "invalid api key", "authentication")
                ):

                    raise

                logger.info("Z.ai model %s did not answer: %s", model, error)

        raise last_error

    # Vision models, best first: these read a screenshot.
    VISION_MODELS = (
        "glm-5v-turbo",
        "glm-4.6v",
        "glm-4.5v",
    )

    def _image_url(self, image_path: str) -> str:
        """A data URL the OpenAI-style vision API accepts."""

        path = Path(image_path)

        data = base64.b64encode(path.read_bytes()).decode("ascii")

        suffix = path.suffix.lower().lstrip(".") or "png"

        mime = "jpeg" if suffix in ("jpg", "jpeg") else suffix

        return f"data:image/{mime};base64,{data}"

    def see(self, question: str, image_path: str) -> dict:
        """Ask the vision model about a screenshot."""

        if not self.health():

            return {
                "success": False,
                "provider": self.name(),
                "error": "ZAI_API_KEY is not set.",
            }

        if _paid_down():

            # Its vision models need credit; skip the doomed requests.
            return {
                "success": False,
                "provider": self.name(),
                "error": "z.ai vision needs a recharge, so the free fallback is used.",
            }

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {
                        "type": "image_url",
                        "image_url": {"url": self._image_url(image_path)},
                    },
                ],
            }
        ]

        first = (settings.ZAI_VISION_MODEL or self.VISION_MODELS[0]).strip()

        candidates = [first] + [
            name for name in self.VISION_MODELS if name != first
        ]

        last_error = None

        for model in candidates:

            try:

                reply = self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=int(settings.ZAI_VISION_MAX_TOKENS),
                    temperature=0.3,
                )

                content = reply.choices[0].message.content

                return {
                    "success": True,
                    "provider": self.name(),
                    "model": getattr(reply, "model", model),
                    "answer": content if isinstance(content, str) else str(content),
                }

            except Exception as error:

                last_error = error

                if _is_balance_error(error):

                    _mark_paid_down()

                    break

                text = str(error).lower()

                if any(
                    word in text
                    for word in ("401", "unauthorized", "invalid api key", "authentication")
                ):

                    break

                logger.info("Z.ai vision model %s did not answer: %s", model, error)

        return {
            "success": False,
            "provider": self.name(),
            "error": str(last_error),
        }

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
