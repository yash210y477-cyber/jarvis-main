import os

from dotenv import load_dotenv


load_dotenv()


class Settings:

    # Gemini

    GEMINI_MODEL = "gemini-2.5-flash"

    # OpenRouter

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    OPENROUTER_MODEL = "openrouter/auto"

    # Network

    REQUEST_TIMEOUT = 60

    MAX_RETRIES = 1

    # Priority

    PROVIDER_PRIORITY = [

        "gemini",

        "openrouter"

    ]


settings = Settings()