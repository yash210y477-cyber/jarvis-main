import logging

from config.settings import settings

from providers.gemini import GeminiProvider
from providers.openrouter import OpenRouterProvider
from providers.groq import GroqProvider
from providers.cerebras import CerebrasProvider
from providers.deepseek import DeepSeekProvider
from providers.openai import OpenAIProvider


logger = logging.getLogger(__name__)


class AIManager:

    def __init__(self):

        self.providers = []

        provider_map = {

            "gemini": (

                settings.ENABLE_GEMINI,

                GeminiProvider

            ),

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

            "openai": (

                settings.ENABLE_OPENAI,

                OpenAIProvider

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

    def chat(self, prompt: str):

        errors = []

        if not self.providers:

            return {

                "success": False,

                "provider": "manager",

                "error": "No AI providers available."

            }

        for provider in self.providers:

            logger.info(f"Trying {provider.name()}")

            try:

                result = provider.chat(prompt)

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