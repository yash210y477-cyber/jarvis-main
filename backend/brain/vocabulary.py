"""Words the user has already typed, used to fix what a call mishears.

The user types "open postman" in chat; on a call Whisper hears "open post
man". The typed word is stored here and a close enough heard word is quietly
replaced with it, so nobody has to spell anything twice.
"""

import json
import logging
import re
import threading
import time
from difflib import SequenceMatcher
from pathlib import Path

from memory.storage import data_dir

logger = logging.getLogger(__name__)

STORE = data_dir() / "vocabulary.json"
MAX_WORDS = 4000
MIN_WORD = 4
MIN_RATIO = 0.72

_lock = threading.RLock()
_words = {}
_loaded = False
_last_save = 0.0

# Never "repair" these into something else; they are already understood.
_COMMON = {
    "open", "close", "play", "pause", "search", "start", "stop", "next",
    "previous", "volume", "mute", "music", "song", "songs", "video", "please",
    "jarvis", "what", "when", "where", "which", "hello", "thanks", "thank",
    "kholo", "band", "bajao", "gaana", "karo", "kya", "hai", "music",
    "chrome", "youtube", "spotify", "google", "notepad", "calculator",
}


def _load():
    global _loaded, _words

    if _loaded:

        return

    _loaded = True

    _seed_from_history()

    try:

        if STORE.exists():

            data = json.loads(STORE.read_text(encoding="utf-8"))

            if isinstance(data, dict):

                _words = {
                    str(word): int(count)
                    for word, count in data.items()
                    if isinstance(count, (int, float)) and str(word)
                }

    except Exception as error:

        logger.debug("Vocabulary load failed: %s", error)

        _words = {}


def _seed_from_history() -> None:
    """First run: learn from the chats that were saved before this store."""

    if STORE.exists():

        return

    try:

        from memory.storage import Storage

        # Counted directly: learn() would re-enter this loader.
        for row in Storage().messages(limit=500):

            if row.get("role") != "user":

                continue

            for word in tokens(row.get("text", "")):

                if len(word) < MIN_WORD or word in _COMMON:

                    continue

                _words[word] = _words.get(word, 0) + 1

    except Exception as error:

        logger.debug("Vocabulary seed skipped: %s", error)


def _maybe_save(force: bool = False) -> None:
    global _last_save

    now = time.monotonic()

    if not _words and not force:

        return

    if not force and now - _last_save < 5.0:

        return

    _last_save = now

    try:

        STORE.parent.mkdir(parents=True, exist_ok=True)

        STORE.write_text(json.dumps(_words, indent=0), encoding="utf-8")

    except OSError as error:

        logger.debug("Vocabulary save failed: %s", error)


def tokens(text: str):
    """Alphabetic words only, so punctuation never ends up in the store."""

    return re.findall(r"[a-zA-Z][a-zA-Z']+", (text or "").lower())


def learn(message: str, force_save: bool = False) -> None:
    """Remember the words a chat message used (silent, cheap, batched)."""

    try:

        with _lock:

            _load()

            new_word = False

            for word in tokens(message):

                if len(word) < MIN_WORD or word in _COMMON:

                    continue

                if word not in _words:

                    new_word = True

                _words[word] = _words.get(word, 0) + 1

            if len(_words) > MAX_WORDS:

                keep = sorted(_words.items(), key=lambda item: -item[1])[:MAX_WORDS]

                _words.clear()

                _words.update(dict(keep))

            # A brand-new word is written at once; repeats are batched.
            _maybe_save(force_save or new_word)

    except Exception as error:

        logger.debug("Vocabulary learn skipped: %s", error)


def _soundex(word: str) -> str:
    """Cheap phonetic key: "postman" and "postmen" land in the same bucket."""

    codes = {
        **dict.fromkeys("bfpv", "1"),
        **dict.fromkeys("cgjkqsxz", "2"),
        **dict.fromkeys("dt", "3"),
        "l": "4",
        **dict.fromkeys("mn", "5"),
        "r": "6",
    }

    letters = [character for character in word.lower() if character.isalpha()]

    if not letters:

        return ""

    first, rest = letters[0], letters[1:]

    digits = []

    for character in rest:

        code = codes.get(character, "")

        if code and (not digits or digits[-1] != code):

            digits.append(code)

    return (first + "".join(digits) + "000")[:4]


def _best_match(word: str):
    """Closest typed word for a heard word, or None when unsure."""

    # Only half the word made it through the line: "post" for "postman".
    if len(word) >= 3:

        starts = [
            c
            for c in _words
            if c.startswith(word) and c != word and len(c) <= len(word) + 5
        ]

        if len(starts) == 1:

            return starts[0]

    # Very short words are only trusted as a prefix, never as a soft match.
    if len(word) < 4:

        return None

    best = None
    best_score = 0.0
    key = _soundex(word)

    for candidate in _words:

        if candidate == word or len(candidate) < MIN_WORD:

            continue

        ratio = SequenceMatcher(None, word, candidate).ratio()

        if _soundex(candidate) == key:

            ratio += 0.15

        if word[:1] == candidate[:1]:

            ratio += 0.05

        if ratio > best_score:

            best, best_score = candidate, ratio

    if best_score >= MIN_RATIO + 0.08:

        return best

    return None


def repair(text: str) -> str:
    """Swap misheard words for ones the user has typed before."""

    heard = (text or "").strip()

    if not heard:

        return heard

    try:

        with _lock:

            _load()

            if not _words:

                return heard

            parts = heard.split()

            fixed = []

            index = 0

            while index < len(parts):

                word = parts[index].strip(".,!?").lower()

                # "post man" was one word when the user typed it.
                if index + 1 < len(parts):

                    joined = (
                        word + parts[index + 1].strip(".,!?").lower()
                    )

                    if len(joined) >= MIN_WORD and joined in _words:

                        fixed.append(joined)

                        index += 2

                        continue

                    glued = _best_match(joined)

                    if glued and SequenceMatcher(None, joined, glued).ratio() >= 0.85:

                        fixed.append(glued)

                        index += 2

                        continue

                if len(word) < 3 or word in _COMMON or word in _words:

                    fixed.append(parts[index])

                    index += 1

                    continue

                match = _best_match(word)

                fixed.append(match if match else parts[index])

                index += 1

            repaired = " ".join(fixed)

            if repaired != heard:

                logger.info("Call words repaired: %r -> %r", heard, repaired)

            return repaired

    except Exception as error:

        logger.debug("Vocabulary repair skipped: %s", error)

        return heard
