"""
Canonical keys for remembered facts.

Users phrase the same fact many ways ("favourite colour", "fav color",
"colour name"). Everything is normalised to one key so recall always finds
what was stored.
"""

import re

# Phrase -> canonical key, applied after basic normalisation.
ALIASES = {
    "fav colour": "favourite_colour",
    "fav color": "favourite_colour",
    "favorite colour": "favourite_colour",
    "favorite color": "favourite_colour",
    "colour": "favourite_colour",
    "color": "favourite_colour",
    "favourite editor": "editor",
    "favorite editor": "editor",
    "fav editor": "editor",
    "favourite language": "favourite_language",
    "favorite language": "favourite_language",
    "fav language": "favourite_language",
    "favourite laptop": "laptop",
    "favorite laptop": "laptop",
    "favourite phone": "phone",
    "favorite phone": "phone",
    "favourite bike": "bike",
    "favorite bike": "bike",
    "fav food": "favourite_food",
    "favorite food": "favourite_food",
    "fav movie": "favourite_movie",
    "favorite movie": "favourite_movie",
    "fav song": "favourite_song",
    "favorite song": "favourite_song",
    "where i live": "city",
    "living": "city",
    "location": "city",
    "job": "occupation",
    "work": "occupation",
    "profession": "occupation",
    "mail": "email",
}

# Words removed from the end of a recall phrase: "city name" -> "city".
TAIL_NOISE = ("name", "value", "again", "please")

# Words removed from the start: "the colour" -> "colour".
HEAD_NOISE = ("the", "my", "your", "a", "an")


def _normalise_words(phrase: str) -> str:
    text = (phrase or "").lower().strip()

    text = re.sub(r"[^a-z0-9\s_-]", " ", text)

    return re.sub(r"\s+", " ", text).strip()


def canonical_key(phrase: str) -> str:
    """Turn a user phrase into the key a fact is stored under."""

    text = _normalise_words(phrase)

    if not text:
        return ""

    words = text.split(" ")

    while len(words) > 1 and words[0] in HEAD_NOISE:
        words.pop(0)

    while len(words) > 1 and words[-1] in TAIL_NOISE:
        words.pop()

    text = " ".join(words).replace("_", " ")

    if not text:
        return ""

    text = text.replace("favorite", "favourite").replace("color", "colour")

    text = ALIASES.get(text, text)

    return text.replace(" ", "_")


def human_key(key: str) -> str:
    """Stored key -> how it reads in a sentence."""

    return (key or "").replace("_", " ").strip()
