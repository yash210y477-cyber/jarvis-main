"""Pick the reply language from what the user actually typed.

Hinglish only when the message looks like Hinglish; English otherwise, so a
plain English sentence is never answered in Hinglish.
"""

import re

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
