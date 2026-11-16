"""Z.ai (Zhipu GLM) through its OpenAI-compatible endpoint."""

import base64
import json
import logging
import os
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from config.settings import settings
from providers.base import BaseProvider
from providers.tool_call import OpenAIToolMixin

load_dotenv()

logger = logging.getLogger(__name__)

# z.ai's free models cost nothing and always answer. The paid ones need a
# topped-up balance and reply 429 "Insufficient balance or no resource package"
# without one, so they are only asked after a paid call really worked.
BALANCE_COOLDOWN = 1800

PAID_OK_FOR = 24 * 3600

# One cheap paid ping every few hours notices a top-up without ever delaying
# a reply.
PROBE_EVERY = 6 * 3600

PROBE_ENABLED = True

FREE_MODELS = ("glm-4.7-flash", "glm-4.5-flash")

FREE_VISION_MODELS = ("glm-4.6v-flash",)

PAID_MODELS = ("glm-5.3", "glm-4.7", "glm-4.6", "glm-4.5", "glm-4.5-air")

PAID_VISION_MODELS = ("glm-5v-turbo", "glm-4.6v", "glm-4.5v")

# A free model that takes longer than this is treated as slow: the fast keys
# then answer first for a while instead of every reply waiting on it.
SLOW_SECONDS = 8

SLOW_COOLDOWN = 1800

_state = {
    "down_until": 0.0,
    "paid_ok_at": 0.0,
    "probe_at": 0.0,
    "slow_until": 0.0,
}

_loaded = False


def _is_timeout(error) -> bool:

    text = str(error).lower()

    return "timeout" in text or "timed out" in text or "Timeout" in type(error).__name__


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
    """The wallet note survives a restart, so nothing has to be re-probed."""

    from memory.storage import data_dir

    return data_dir() / "zai_wallet.json"


def _load() -> None:

    global _loaded

    if _loaded:

        return

    _loaded = True

    try:

        saved = json.loads(_state_file().read_text(encoding="utf-8"))

    except (OSError, ValueError):

        return

    for key in _state:

        try:

            _state[key] = float(saved.get(key) or 0)

        except (TypeError, ValueError):

            _state[key] = 0.0


def _save() -> None:

    try:

        _state_file().write_text(json.dumps(_state), encoding="utf-8")

    except OSError:

        pass


def _paid_down() -> bool:

    _load()

    return time.time() < _state["down_until"]


def _paid_ok() -> bool:
    """A paid model answered recently, so the wallet has credit."""

    _load()

    return time.time() - _state["paid_ok_at"] < PAID_OK_FOR and not _paid_down()


def _mark_paid_down() -> None:

    _load()

    _state["down_until"] = time.time() + BALANCE_COOLDOWN
    _state["paid_ok_at"] = 0.0

    _save()

    logger.info("z.ai has no balance; paid models off for %s min", BALANCE_COOLDOWN // 60)


def _mark_paid_ok(model: str) -> None:

    _load()

    _state["paid_ok_at"] = time.time()
    _state["down_until"] = 0.0

    _save()

    logger.info("z.ai paid model %s answered; balance is back", model)


def _probe_due() -> bool:

    _load()

    return time.time() - _state["probe_at"] > PROBE_EVERY


def _mark_probe() -> None:

    _load()

    _state["probe_at"] = time.time()

    _save()


def paid_down() -> bool:
    """True while the empty wallet keeps the paid models out of the way."""

    return _paid_down()


def paid_ready() -> bool:
    """A paid model answered recently, so it is quick."""

    return _paid_ok()


def slow() -> bool:
    """The free models recently took longer than a reply should."""

    _load()

    return time.time() < _state["slow_until"]


def _mark_slow() -> None:

    _load()

    if time.time() < _state["slow_until"]:

        return

    _state["slow_until"] = time.time() + SLOW_COOLDOWN

    _save()

    logger.info("z.ai free models are slow right now; fast keys go first")


def reset_balance_cooldown() -> None:
    """Forget the wallet state (used after a recharge or by tests)."""

    global _loaded

    _load()

    _state.update(
        {"down_until": 0.0, "paid_ok_at": 0.0, "probe_at": 0.0, "slow_until": 0.0}
    )

    _save()


class ZaiProvider(OpenAIToolMixin, BaseProvider):

    def __init__(self):

        self.provider_name = "zai"

        self.api_key = (os.getenv("ZAI_API_KEY") or "").strip()

        self.base_url = settings.ZAI_BASE_URL

        self.model = settings.ZAI_MODEL

        self.client = None

        self._working = None

        if self.api_key:

            # A slow free model must not hold a reply hostage: after this the
            # next provider gets its turn.
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=float(getattr(settings, "ZAI_TIMEOUT", 20)),
            )

    def name(self) -> str:

        return self.provider_name

    def health(self) -> bool:

        return self.client is not None

    # Free first, then the paid ones.
    MODELS = FREE_MODELS + PAID_MODELS

    def resolve_model(self):

        return FREE_MODELS[0]

    def _candidates(self, first: str) -> list[str]:
        """Free models first, then the paid ones when they may have credit."""

        free = [
            name for name in dict.fromkeys((first, *FREE_MODELS)) if name in FREE_MODELS
        ]

        if _paid_down():

            # Nothing to buy with an empty wallet.
            return free

        return free + [name for name in PAID_MODELS if name not in free]

    def _probe_paid(self) -> None:
        """Ask one paid model in the background so a top-up is noticed."""

        if not PROBE_ENABLED or self.client is None or _paid_ok() or not _probe_due():

            return

        _mark_probe()

        model = PAID_MODELS[0]

        def work():

            try:

                self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                )

                _mark_paid_ok(model)

            except Exception as error:

                if _is_balance_error(error):

                    _mark_paid_down()

        threading.Thread(target=work, daemon=True).start()

    def _ask(self, messages, tools=None, model=None):

        """Ask the candidate models until one answers; remember the winner."""

        first = (model or self.resolve_model()).strip()

        candidates = self._candidates(first)

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

                started = time.time()

                reply = self.client.chat.completions.create(**payload)

                took = time.time() - started

                self._working = model

                if model in FREE_MODELS:

                    # Free answered, so nothing was learned about the balance.
                    if took > SLOW_SECONDS:

                        _mark_slow()

                    self._probe_paid()

                else:

                    _mark_paid_ok(model)

                return reply

            except Exception as error:

                last_error = error

                if _is_timeout(error) and model in FREE_MODELS:

                    # A free model that times out is slow right now; the next
                    # provider should answer instead of another long wait.
                    _mark_slow()

                    raise

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

    # The free vision model reads screenshots without a recharge; the paid
    # ones are added only when the wallet has credit.
    VISION_MODELS = FREE_VISION_MODELS + PAID_VISION_MODELS

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

        # glm-4.6v-flash reads screenshots for free, so it goes first and the
        # paid vision models are only a fallback.
        first = FREE_VISION_MODELS[0]

        candidates = [first]

        if not _paid_down():

            candidates += [name for name in PAID_VISION_MODELS if name != first]

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

                if model not in FREE_VISION_MODELS:

                    _mark_paid_ok(model)

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
                "model": getattr(reply, "model", self._working or "") or "",
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
