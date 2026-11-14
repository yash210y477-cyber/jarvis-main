import inspect
import logging

from config.settings import settings

from providers.openrouter import OpenRouterProvider
from providers.groq import GroqProvider
from providers.cerebras import CerebrasProvider
from providers.deepseek import DeepSeekProvider
from providers.zai import ZaiProvider
from providers.siliconflow import SiliconFlowProvider
from providers.ollama import OllamaProvider


logger = logging.getLogger(__name__)


class AIManager:

    def __init__(self):

        self.providers = []

        provider_map = {


            "openrouter": (

                settings.ENABLE_OPENROUTER,

                OpenRouterProvider

            ),

            "groq": (

                settings.ENABLE_GROQ,

                GroqProvider

            ),

            "cerebras": (

                settings.ENABLE_CEREBRAS,

                CerebrasProvider

            ),

            "deepseek": (

                settings.ENABLE_DEEPSEEK,

                DeepSeekProvider

            ),

            "zai": (

                settings.ENABLE_ZAI,

                ZaiProvider

            ),

            "siliconflow": (

                settings.ENABLE_SILICONFLOW,

                SiliconFlowProvider

            ),


            "ollama": (

                settings.ENABLE_OLLAMA,

                OllamaProvider

            )

        }

        for provider_name in settings.PROVIDER_PRIORITY:

            if provider_name not in provider_map:

                logger.warning(f"Unknown provider: {provider_name}")

                continue

            enabled, provider_class = provider_map[provider_name]

            if not enabled:

                logger.info(f"{provider_name} disabled")

                continue

            try:

                provider = provider_class()

                self.providers.append(provider)

                logger.info(f"{provider.name()} loaded")

            except Exception as e:

                logger.error(f"{provider_name} failed to initialize: {e}")

    def available_providers(self):

        return [

            provider.name()

            for provider in self.providers

        ]

    # What the model picker in the UI sends, and the provider it means.
    ALIASES = {
        "llama3 (local)": "ollama",
        "llama3": "ollama",
        "local": "ollama",
        "gpt-4o": "openrouter",
        "claude": "openrouter",
    }

    def find(self, name):
        """The provider for a picked name, or None for auto/unknown."""

        key = (name or "").strip().lower()

        if key in ("", "auto", "default"):

            return None

        key = self.ALIASES.get(key, key)

        for provider in self.providers:

            if provider.name().lower() == key:

                return provider

        return None

    # Which providers are tried first for a kind of work.
    TASK_ORDER = {
        "coding": ("groq", "openrouter", "zai", "deepseek", "cerebras"),
        "research": ("openrouter", "groq", "zai", "deepseek"),
    }

    def model_for(self, provider_name: str, task):
        """A task-specific model id, or None to keep the provider default."""

        if task == "research" and provider_name == "openrouter":

            online = str(getattr(settings, "RESEARCH_ONLINE", "1")).lower()

            if online not in ("0", "false", "no"):

                base = settings.OPENROUTER_MODEL

                return base if base.endswith(":online") else base + ":online"

        return None

    @staticmethod
    def takes_model(provider) -> bool:
        """True when a provider accepts a per-call model id."""

        try:

            params = inspect.signature(provider.chat).parameters

        except (TypeError, ValueError):

            return False

        return "model" in params or any(

            param.kind is param.VAR_KEYWORD for param in params.values()

        )

    def chat(self, prompt: str, provider=None, task=None):

        errors = []

        chosen = self.find(provider) if isinstance(provider, str) else provider

        if chosen is not None:

            order = [chosen] + [
                item for item in self.providers if item is not chosen
            ]

        else:

            order = list(self.providers)

            # Coding and research lean on the providers that do them best.
            if task in self.TASK_ORDER:

                first = [
                    item
                    for name in self.TASK_ORDER[task]
                    for item in self.providers
                    if item.name() == name
                ]

                if first:

                    order = first + [
                        item for item in self.providers if item not in first
                    ]

        if not self.providers:

            return {

                "success": False,

                "provider": "manager",

                "error": "No AI providers available."

            }

        for provider in order:

            logger.info(f"Trying {provider.name()}")

            try:

                wanted_model = self.model_for(provider.name(), task)

                result = (
                    provider.chat(prompt, model=wanted_model)
                    if wanted_model and self.takes_model(provider)
                    else provider.chat(prompt)
                )

                if result.get("success"):

                    logger.info(f"{provider.name()} success")

                    return result

                logger.warning(

                    f"{provider.name()} failed"

                )

                errors.append({

                    "provider": provider.name(),

                    "error": result.get("error")

                })

            except Exception as e:

                logger.exception(

                    f"{provider.name()} crashed"

                )

                errors.append({

                    "provider": provider.name(),

                    "error": str(e)

                })

        return {

            "success": False,

            "provider": "manager",

            "message": "All AI providers failed.",

            "errors": errors

        }
    def chat_with_tools(self, messages, tools):

        errors = []

        for provider in self.providers:

            if not getattr(provider, "supports_tools", False):

                errors.append({
                    "provider": provider.name(),
                    "error": "tool calling not supported"
                })

                continue

            try:

                result = provider.chat_with_tools(messages, tools)

            except Exception as error:

                errors.append({
                    "provider": provider.name(),
                    "error": str(error)
                })

                continue

            if result.get("success"):

                return result

            errors.append({
                "provider": provider.name(),
                "error": result.get("error")
            })

        return {
            "success": False,
            "provider": "manager",
            "error": "No provider could run tools.",
            "errors": errors
        }
