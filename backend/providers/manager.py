import logging

from config.settings import settings

from providers.gemini import GeminiProvider
from providers.openrouter import OpenRouterProvider
from providers.groq import GroqProvider
from providers.cerebras import CerebrasProvider
from providers.deepseek import DeepSeekProvider
from providers.openai import OpenAIProvider


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are JARVIS, an advanced AI assistant developed by Yash Yadav.

Your identity is always JARVIS.

Never say you are ChatGPT, OpenAI, Gemini, Claude, Groq, DeepSeek, Cerebras or any other AI model.

If someone asks who developed you, reply:
"I am JARVIS, developed by Yash Yadav."

If someone asks who created you, reply:
"I was created by Yash Yadav."

If someone asks if you are ChatGPT or Gemini, reply:
"I am JARVIS. I use advanced AI models internally, but my identity is JARVIS."

Always answer as JARVIS.
""" 

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

                logger.warning(
                    "Unknown provider: %s",
                    provider_name
                )

                continue

            enabled, provider_class = provider_map[
                provider_name
            ]

            if not enabled:

                logger.info(
                    "%s disabled",
                    provider_name
                )

                continue

            try:

                provider = provider_class()

                if provider.health():

                    self.providers.append(
                        provider
                    )

                    logger.info(
                        "%s loaded",
                        provider.name()
                    )

                else:

                    logger.warning(
                        "%s unavailable",
                        provider.name()
                    )

            except Exception:

                logger.exception(
                    "%s failed to initialize",
                    provider_name
                )
    
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

            logger.info(

                "Trying provider: %s",

                provider.name()

            )

            try:

                final_prompt = f"{SYSTEM_PROMPT}\n\nUser: {prompt}"

                result = provider.chat(final_prompt)

                if result.get("success"):

                    logger.info(

                        "%s success",

                        provider.name()

                    )

                    return result

                logger.warning(

                    "%s failed",

                    provider.name()

                )

                errors.append(

                    {

                        "provider": provider.name(),

                        "error": result.get("error")

                    }

                )

            except Exception:

                logger.exception(

                    "%s crashed",

                    provider.name()

                )

                errors.append(

                    {

                        "provider": provider.name(),

                        "error": "Provider crashed"

                    }

                )
                
        return {
                    
            "success": False,
                    
            "provider": "manager",
                    
            "message": "All AI providers failed.",
                    
            "errors": errors
                    
        }
            