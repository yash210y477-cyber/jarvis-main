from pathlib import Path

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:

    # ==========================================================
    # APPLICATION
    # ==========================================================

    APP_NAME = "JARVIS"

    APP_VERSION = "1.0.0"

    DEBUG = True

    # ==========================================================
    # NETWORK
    # ==========================================================

    REQUEST_TIMEOUT = 60

    MAX_RETRIES = 2

    # Optional extra secret for state-changing requests (X-Jarvis-Token).
    LOCAL_TOKEN = os.getenv("JARVIS_LOCAL_TOKEN", "")

    # Root folder the sandboxed file/shell tools may touch.
    WORKSPACE_ROOT = str(Path(__file__).resolve().parents[2])

    # Origins allowed to call the API (the Mina web UI).
    ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    # ==========================================================
    # GEMINI
    # ==========================================================

    GEMINI_MODEL = "gemini-2.5-flash"

    # ==========================================================
    # OPENROUTER
    # ==========================================================

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    OPENROUTER_MODEL = "openrouter/auto"

    # ==========================================================
    # GROQ
    # ==========================================================

    GROQ_MODEL = "llama-3.3-70b-versatile"

    # ==========================================================
    # CEREBRAS
    # ==========================================================

    CEREBRAS_MODEL = "gpt-oss-120b"

    # ==========================================================
    # DEEPSEEK
    # ==========================================================

    DEEPSEEK_BASE_URL = "https://api.deepseek.com"

    DEEPSEEK_MODEL = "deepseek-chat"

    # ==========================================================
    # OPENAI
    # ==========================================================

    OPENAI_MODEL = "gpt-4.1-mini"

    # ==========================================================
    # ENABLE / DISABLE PROVIDERS
    # ==========================================================

    ENABLE_GEMINI = True

    ENABLE_OPENROUTER = True

    ENABLE_GROQ = True

    ENABLE_CEREBRAS = True

    ENABLE_DEEPSEEK = True

    ENABLE_OPENAI = True

    # ==========================================================
    # PROVIDER PRIORITY
    # ==========================================================

    PROVIDER_PRIORITY = [

        "gemini",

        "openrouter",

        "groq",

        "cerebras",

        "deepseek",

        "openai"

    ]

    # ==========================================================
    # LOGGING
    # ==========================================================

    LOG_LEVEL = "INFO"

    LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


settings = Settings()