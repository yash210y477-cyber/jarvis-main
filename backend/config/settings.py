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

    # Speech recognition model: "base" is fast but mishears Hinglish
    # commands on phone audio, "small" is the accuracy/speed sweet spot.
    STT_MODEL = os.getenv("STT_MODEL", "small")

    # "auto" lets Whisper decide per clip, so Hindi and Hinglish are heard as
    # they are instead of being forced through English.
    STT_LANGUAGE = os.getenv("STT_LANGUAGE", "auto")

    STT_COMPUTE_TYPE = os.getenv("STT_COMPUTE_TYPE", "int8")

    STT_THREADS = _int_env("STT_THREADS", 4)

    # Neural speech for replies (edge = natural, sapi = offline robotic).
    TTS_ENGINE = os.getenv("TTS_ENGINE", "sapi")

    TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AndrewNeural")

    # The six voices offered in Settings: three male, three female, with one
    # Indian voice of each.
    VOICE_OPTIONS = (
        {"id": "en-IN-PrabhatNeural", "name": "Prabhat", "gender": "male", "accent": "Indian English"},
        {"id": "en-US-AndrewMultilingualNeural", "name": "Andrew", "gender": "male", "accent": "US English, multilingual"},
        {"id": "en-GB-RyanNeural", "name": "Ryan", "gender": "male", "accent": "British English"},
        {"id": "en-IN-NeerjaNeural", "name": "Neerja", "gender": "female", "accent": "Indian English"},
        {"id": "en-US-JennyNeural", "name": "Jenny", "gender": "female", "accent": "US English"},
        {"id": "en-US-AriaNeural", "name": "Aria", "gender": "female", "accent": "US English, expressive"},
    )

    # Where the screenshots the user asked for are kept. Empty means
    # Downloads/Jarvis, the same folder every saved file goes to.
    SCREENSHOT_DIR = os.getenv("SCREENSHOT_DIR", "")

    # Windows speech keeps call replies instant; edge sounds natural but
    # needs the network and about two seconds before it can speak.
    TTS_SAPI_VOICE = os.getenv("TTS_SAPI_VOICE", "Microsoft Zira Desktop")

    TTS_SAPI_RATE = int(os.getenv("TTS_SAPI_RATE", "1"))

    # How long a pause ends the caller's sentence; shorter feels faster.
    TELEGRAM_CALL_SILENCE_SECONDS = float(
        os.getenv("TELEGRAM_CALL_SILENCE_SECONDS", "0.7")
    )

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

    # Backend Swagger UI
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

    # ==========================================================
    # OPENROUTER
    # ==========================================================

    OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

    OPENROUTER_MODEL = "openrouter/auto"

    # A small cap keeps the free request under its limit.
    OPENROUTER_MAX_TOKENS = int(os.getenv("OPENROUTER_MAX_TOKENS", "512"))

    # Free vision models used when z.ai's free vision model fails.
    OPENROUTER_VISION_MODELS = tuple(
        name.strip()
        for name in os.getenv(
            "OPENROUTER_VISION_MODELS",
            "inclusionai/ling-3.2-flash:free,nvidia/nemotron-3.5-super-vl:free,"
            "particle-ai/particle-1:free",
        ).split(",")
        if name.strip()
    )

    # Research answers check the web through OpenRouter's :online models.
    RESEARCH_ONLINE = os.getenv("RESEARCH_ONLINE", "1")

    # ==========================================================
    # IMAGE GENERATION (OpenRouter images endpoint)
    # ==========================================================

    IMAGE_MODEL = os.getenv(
        "IMAGE_MODEL", "recraft/recraft-v4.1-flash-v2:free"
    )

    # ==========================================================
    # GROQ
    # ==========================================================

    GROQ_MODEL = os.getenv("GROQ_MODEL", "minimaxai/minimax-m2.7")

    # Groq retires models; this one answers when the first choice is gone.
    GROQ_FALLBACK_MODEL = os.getenv(
        "GROQ_FALLBACK_MODEL", "llama-3.3-70b-versatile"
    )

    GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "2048"))

    # ==========================================================
    # Z.AI (GLM models, OpenAI-compatible endpoint)
    # ==========================================================

    ZAI_BASE_URL = os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/")

    # The free model the provider answers with.
    ZAI_MODEL = os.getenv("ZAI_MODEL", "glm-4.7-flash")

    ZAI_MAX_TOKENS = int(os.getenv("ZAI_MAX_TOKENS", "2048"))

    # Seconds a z.ai call may take before the next provider answers instead.
    ZAI_TIMEOUT = float(os.getenv("ZAI_TIMEOUT", "20"))

    # Vision: reads screenshots, including open web pages.
    ZAI_VISION_MAX_TOKENS = int(os.getenv("ZAI_VISION_MAX_TOKENS", "900"))

    # Screen watching: explain pages and pointed-at things without a command.
    SCREEN_WATCH_INTERVAL = int(os.getenv("SCREEN_WATCH_INTERVAL", "8"))

    SCREEN_WATCH_COOLDOWN = int(os.getenv("SCREEN_WATCH_COOLDOWN", "25"))

    SCREEN_WATCH_PAGE_DIFF = float(os.getenv("SCREEN_WATCH_PAGE_DIFF", "18"))

    SCREEN_WATCH_DWELL = float(os.getenv("SCREEN_WATCH_DWELL", "1.6"))

    SCREEN_WATCH_CROP = int(os.getenv("SCREEN_WATCH_CROP", "420"))

    SCREEN_WATCH_SPEAK = os.getenv("SCREEN_WATCH_SPEAK", "1")

    # Hold Ctrl+Alt to talk (push-to-talk companion).
    COMPANION_AUTOSTART = os.getenv("COMPANION_AUTOSTART", "1") not in (
        "0", "false", "False", "no"
    )


    # ==========================================================
    # LANGUAGE + SEMANTIC MEMORY
    # ==========================================================

    # hinglish (default), english or hindi.
    # auto / english / hinglish — the final say is the choice saved in Settings.
    JARVIS_LANGUAGE = os.getenv("JARVIS_LANGUAGE", "auto")

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

    ENABLE_OPENROUTER = True

    ENABLE_GROQ = True

    ENABLE_ZAI = True

    # ==========================================================
    # PROVIDER PRIORITY
    # ==========================================================

    PROVIDER_PRIORITY = [

        "zai",

        "openrouter",

        "groq",

        # Local fallback: answers when every cloud key above fails.
        "ollama"

    ]

    # ==========================================================
    # LOGGING
    # ==========================================================

    LOG_LEVEL = "INFO"

    LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"


settings = Settings()