"""Which language JARVIS answers in.

Settings offers three modes: english (always English), hinglish (always
Hinglish) and auto (follow whatever the user wrote). Auto is the default, so a
plain English sentence is never answered in Hinglish unless the user chose it.
"""

import re
from pathlib import Path

MODES = ("auto", "english", "hinglish")

LABELS = {
    "auto": "Auto (match the user's language)",
    "english": "English",
    "hinglish": "Hinglish",
}

DEFAULT = "auto"

DEVANAGARI = re.compile(r"[\u0900-\u097F]")

# Words that only show up in Hinglish/Hindi romanisation.
STRONG = frozenset({
    "kya", "kaise", "kaisa", "kaisi", "kyun", "kyu", "kahan", "kab", "kitna",
    "kitne", "karo", "kro", "karna", "krna", "kholo", "khol", "bajao", "batao",
    "bata", "bataao", "mujhe", "mera", "meri", "mere", "tum", "tumhara",
    "tumhari", "aap", "aapka", "yaar", "bhai", "bhaiya", "nahi", "nahin",
    "samajh", "suno", "bolo", "raha", "rahi", "rha", "rhi", "banao", "dikhao",
    "lagao", "chalu", "chalao", "yaad", "dilana", "shukriya", "dhanyawad",
    "namaste", "theek", "thik", "acha", "accha", "haan", "abhi", "mahina",
    "tareekh", "baje", "awaaz", "awaz", "zara", "jyada", "zyada", "kaam",
    "hafte", "kaunsa", "konsa", "din",
})

# Romanised words that also appear in normal English.
WEAK = frozenset({"hai", "hain", "hoon", "kar", "band", "kam", "tez", "sab", "kal"})


def _file() -> Path:
    """Where the chosen mode is kept, next to the other data files."""

    from memory.storage import data_dir

    return Path(data_dir()) / "language.txt"


def current() -> str:
    """The mode in use: auto, english or hinglish."""

    try:

        saved = _file().read_text(encoding="utf-8").strip().lower()

    except Exception:

        saved = ""

    if saved in MODES:

        return saved

    # Nothing chosen yet: the env var (if any) still decides, auto otherwise.
    from config.settings import settings

    fallback = (getattr(settings, "JARVIS_LANGUAGE", "") or "").strip().lower()

    return fallback if fallback in MODES else DEFAULT


def set_language(mode: str) -> str:
    """Remember the user's choice; it survives a restart."""

    wanted = (mode or "").strip().lower()

    if wanted not in MODES:

        raise ValueError(f"Unknown reply language: {mode}")

    path = _file()

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(wanted, encoding="utf-8")

    return wanted


def options() -> list:
    """The three choices Settings shows, in order."""

    return [{"id": mode, "label": LABELS[mode]} for mode in MODES]


def reply_language(message: str) -> str:
    """english or hinglish, for this message and the chosen mode."""

    mode = current()

    if mode == "auto":

        return "hinglish" if is_hinglish(message) else "english"

    return mode


def is_hinglish(text: str) -> bool:
    """True when the message is written in Hinglish or Devanagari."""

    message = (text or "").strip().lower()

    if not message:
        return False

    if DEVANAGARI.search(message):
        return True

    words = re.findall(r"[a-z']+", message)

    if not words:
        return False

    if any(word in STRONG for word in words):
        return True

    weak_hits = sum(1 for word in words if word in WEAK)

    return weak_hits >= 2
