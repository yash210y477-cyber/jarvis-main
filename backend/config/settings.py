from pathlib import Path

import os

from dotenv import load_dotenv

load_dotenv()


def _int_env(name: str, default: int) -> int:
    """Read an int from the environment, tolerating placeholder values."""

    raw = (os.getenv(name) or "").strip()

    try:

        return int(raw)

    except ValueError:

        return default


def _float_env(name: str, default: float) -> float:

    raw = (os.getenv(name) or "").strip()

    try:

        return float(raw)

    except ValueError:

        return default


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

    # ==========================================================
    # PROACTIVE + REMOTE
    # ==========================================================

    NOTIFICATIONS_ENABLED = os.getenv("JARVIS_NOTIFICATIONS", "1") not in (
        "0", "false", "False", "no"
    )

    # Telegram bot bridge (optional, leave empty to disable).
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

    TELEGRAM_ALLOWED_CHAT_IDS = [
        item.strip()
        for item in os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", "").split(",")
        if item.strip()
    ]

    # Telegram user account for real voice calls (bots cannot call).
    TELEGRAM_API_ID = _int_env("TELEGRAM_API_ID", 0)

    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")

    TELEGRAM_CALL_AUTO_ANSWER = os.getenv(
        "TELEGRAM_CALL_AUTO_ANSWER", "1"
    ) not in ("0", "false", "False", "no")

    # Optional ready-made greeting clip; otherwise one is generated locally.
    TELEGRAM_CALL_GREETING = os.getenv("TELEGRAM_CALL_GREETING", "")

    # Phase B: actually talk on the call (listen, think, answer).
    TELEGRAM_CALL_CONVERSATION = os.getenv(
        "TELEGRAM_CALL_CONVERSATION", "1"
    ) not in ("0", "false", "False", "no")

    # "auto" lets Whisper guess (Hinglish works); or "en", "hi", ...
    TELEGRAM_CALL_LANGUAGE = os.getenv("TELEGRAM_CALL_LANGUAGE", "auto")

    # Only these Telegram user ids may reach JARVIS (empty = anyone).
    TELEGRAM_CALL_ALLOWED = [
        item.strip()
        for item in os.getenv("TELEGRAM_CALL_ALLOWED", "").split(",")
        if item.strip()
    ]

    MORNING_BRIEFING_HOUR = _int_env("JARVIS_BRIEFING_HOUR", 8)

    MORNING_BRIEFING_MINUTE = _int_env("JARVIS_BRIEFING_MINUTE", 30)

    # Origins allowed to call the API (the Mina web UI).
    ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",

    # Swagger UI
    "http://localhost:8000",
    "http://127.0.0.1:8000",
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
    # LANGUAGE + SEMANTIC MEMORY
    # ==========================================================

    # hinglish (default), english or hindi.
    JARVIS_LANGUAGE = os.getenv("JARVIS_LANGUAGE", "hinglish")

    SEMANTIC_MEMORY = os.getenv("SEMANTIC_MEMORY", "1") not in (
        "0", "false", "False", "no"
    )

    SEMANTIC_MODEL = os.getenv(
        "SEMANTIC_MODEL",
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    )

    SEMANTIC_TOP_K = _int_env("SEMANTIC_TOP_K", 3)

    SEMANTIC_MIN_SCORE = _float_env("SEMANTIC_MIN_SCORE", 0.28)

    # ==========================================================
    # OLLAMA (local model, no API key)
    # ==========================================================

    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

    # Empty = use the first installed model (qwen is preferred).
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "")

    # Local generation on CPU is slow, so give it room.
    OLLAMA_TIMEOUT = _float_env("OLLAMA_TIMEOUT", 90.0)

    OLLAMA_MAX_TOKENS = _int_env("OLLAMA_MAX_TOKENS", 120)

    # Prompt characters sent to the local model (it runs on CPU).
    OLLAMA_PROMPT_CHARS = _int_env("OLLAMA_PROMPT_CHARS", 1200)

    ENABLE_OLLAMA = os.getenv("ENABLE_OLLAMA", "1") not in (
        "0", "false", "False", "no"
    )

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

        "openai",

        # Local fallback: answers when every cloud key above fails.
        "ollama"

    ]

    # ==========================================================
    # LOGGING
    # ==========================================================

    LOG_LEVEL = "INFO"

    LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


settings = Settings()