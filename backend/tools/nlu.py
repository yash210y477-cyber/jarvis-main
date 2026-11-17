"""Understand loosely spoken commands, in any word order.

Fixed patterns like "open spotify" break the moment the words move
("spotify open", "search song on spotify", "mujhe gaana bajao youtube pe").
This module reads the sentence instead: it finds the action words, the site
name and the app name wherever they appear, and keeps the rest as the query.
"""

import difflib
import re

from tools import browser

# --------------------------------------------------------------------- words

OPEN_WORDS = {"open", "launch", "start", "kholo", "khol", "khulo", "chalu", "chala", "chalao"}
OPEN_EXTRA = {"kholna", "kholo."}

CLOSE_WORDS = {"close", "quit", "exit", "kill", "band", "hata", "hatao", "off"}

SEARCH_WORDS = {
    "search", "find", "lookup", "look", "google", "dhundo", "dhoondo", "dhunde",
    "khojo", "khoj", "chaan", "chhan", "browse",
}

PLAY_WORDS = {"play", "bajao", "baja", "bajana", "suno", "sunna", "gaana", "gana", "song", "music", "video"}

PAUSE_WORDS = {"pause", "roko", "ruk", "stop"}
NEXT_WORDS = {"next", "agla", "agli", "skip"}
PREV_WORDS = {"previous", "prev", "pichla", "pichhla", "pichli"}

VOLUME_WORDS = {"volume", "awaaz", "awaz", "sound"}
UP_WORDS = {"up", "badhao", "badha", "zyada", "zada", "tez", "increase", "louder"}
DOWN_WORDS = {"down", "kam", "ghatao", "ghata", "decrease", "quieter", "slow"}

# "stop", "next" and "zyada" are ordinary words too, so a playback verb only
# counts when the sentence is plainly about media ("pause music") or when the
# verb is the whole request ("stop", "next").
MUSIC_CONTEXT = {
    "music", "song", "songs", "track", "tracks", "video", "playback",
    "playlist", "audio", "gaana", "gana", "ganaa", "bajao", "baja",
    "spotify", "youtube", "netflix", "hotstar",
}

SITES = {
    "youtube", "spotify", "google", "github", "wikipedia", "amazon", "flipkart",
    "instagram", "facebook", "twitter", "x", "reddit", "netflix", "hotstar",
    "whatsapp", "gmail", "maps", "chatgpt", "stackoverflow", "linkedin",
}

FILLER = {
    "jarvis", "please", "pls", "plz", "zara", "abhi", "bhai", "yaar", "na",
    "kar", "karo", "kro", "krdo", "kr", "do", "de", "dijiye", "dena", "deni",
    "jao", "ja",
    "mera", "mere", "meri", "mujhe", "mai", "main", "me", "tum", "aap", "you",
    "the", "a", "an", "app", "application", "program", "programme", "for",
    "on", "in", "pe", "par", "se", "to", "ka", "ki", "ke", "ko", "ek", "kuch",
    "hey", "ok", "okay", "and", "then", "phir", "now", "can", "could",
    "would", "will", "want", "need", "chahiye", "hai", "ho", "hona", "karna",
    "karva", "karwa", "ga", "gaa", "liye", "liya", "raha", "rahi",
}



IMAGE_NOUNS = {
    "image", "images", "picture", "pictures", "pic", "photo", "wallpaper",
    "drawing", "sketch", "painting",
}

IMAGE_VERBS = {
    "generate", "create", "make", "draw", "paint", "render", "design",
    "banao", "bana", "banado", "banade", "banaao", "banaa",
}

# Dropped from the description so the prompt reads like a description.
# "draw a dragon": the verb alone is enough to mean a picture.
DRAW_VERBS = {
    "draw", "paint", "sketch", "render", "banao", "banado", "banade",
    "banaao", "banaa",
}

ARTICLES = {"a", "an", "the"}

IMAGE_NOISE = {
    "jarvis", "please", "pls", "plz", "for", "me", "mujhe", "do", "of",
}


def _picture_prompt(message: str):
    """The description inside "generate an image of a cat", or None."""

    words = _words(message)

    # "search for an image of ..." is a web search, not a drawing.
    if any(word in SEARCH_WORDS for word in words):

        return None

    wants_picture = any(word in IMAGE_NOUNS for word in words) or any(
        word in DRAW_VERBS for word in words
    )

    if not wants_picture:

        return None

    keep = [
        word
        for word in words
        if word not in IMAGE_NOUNS
        and word not in IMAGE_VERBS
        and word not in IMAGE_NOISE
    ]

    # "an a cat" reads badly, so a run of articles keeps only its last.
    tidy = []

    for word in keep:

        if word in ARTICLES and tidy and tidy[-1] in ARTICLES:

            tidy[-1] = word

            continue

        tidy.append(word)

    return " ".join(tidy).strip()


def _words(text):
    return re.findall(r"[a-z0-9+.#&'-]+", (text or "").lower())


def _app_names():
    try:
        from tools import launcher

        return set(launcher.ALIASES) | set(launcher.KNOWN_PATHS)

    except Exception:

        return set()


def _match_app(spoken):
    """App name from the launcher's list, tolerating a typo."""

    if not spoken:

        return ""

    try:
        from tools import launcher

        if spoken in launcher.ALIASES:

            return launcher.ALIASES[spoken]

    except Exception:

        pass

    names = _app_names()

    if spoken in names:

        return spoken

    close = difflib.get_close_matches(spoken, sorted(names), n=1, cutoff=0.8)

    return close[0] if close else ""


def _match_site(token):
    if token in SITES:

        return token

    close = difflib.get_close_matches(token, sorted(SITES), n=1, cutoff=0.85)

    return close[0] if close else ""


def interpret(message: str):
    """Return a tool intent for a loosely spoken sentence, or None."""

    picture = _picture_prompt(message)

    if picture:

        return {"tool": "generate_image", "arguments": {"prompt": picture}}

    words = _words(message)

    if not words:

        return None

    tokens = [word for word in words if word not in FILLER]

    if not tokens:

        return None

    verb_set = (
        OPEN_WORDS | CLOSE_WORDS | SEARCH_WORDS | PLAY_WORDS
        | PAUSE_WORDS | NEXT_WORDS | PREV_WORDS | VOLUME_WORDS
    )

    site = ""

    rest = []

    for token in tokens:

        matched_site = _match_site(token) if token not in verb_set else ""

        if matched_site and not site:

            site = matched_site

        else:

            rest.append(token)

    action_words = {token for token in tokens if token in verb_set}

    left = [token for token in rest if token not in verb_set]

    phrase = " ".join(left)

    # ---- volume -------------------------------------------------------
    # Only a spoken volume word asks for the volume; "thoda zyada bata do" is
    # a request for more detail, not for a louder speaker.
    if (action_words | set(words)) & VOLUME_WORDS:

        if any(word in DOWN_WORDS for word in left):

            return {
                "tool": "media_control",
                "arguments": {"action": "volume_down", "steps": 1},
            }

        if any(word in UP_WORDS for word in left):

            return {
                "tool": "media_control",
                "arguments": {"action": "volume_up", "steps": 1},
            }

    # ---- music transport ----------------------------------------------
    playing = bool(set(words) & MUSIC_CONTEXT) or not left

    if playing and action_words & PAUSE_WORDS:

        return {
            "tool": "media_control",
            "arguments": {"action": "play_pause", "steps": 1},
        }

    if playing and action_words & NEXT_WORDS:

        return {
            "tool": "media_control",
            "arguments": {"action": "next", "steps": 1},
        }

    if playing and action_words & PREV_WORDS:

        return {
            "tool": "media_control",
            "arguments": {"action": "previous", "steps": 1},
        }

    # ---- search on a site: "search song on spotify" -------------------
    if site and (action_words & SEARCH_WORDS):

        query = phrase or "song"

        return {"tool": "search_site", "arguments": {"query": query, "site": site}}

    # ---- play something, maybe on a site ------------------------------
    if site and (action_words & PLAY_WORDS):

        query = phrase or "songs"

        return {"tool": "search_site", "arguments": {"query": query, "site": site}}

    # ---- close first: "spotify band karo" -----------------------------
    if action_words & CLOSE_WORDS:

        app = _match_app(phrase)

        if app:

            return {"tool": "close_app", "arguments": {"app_name": app}}

        if phrase and len(left) <= 3:

            return {"tool": "close_app", "arguments": {"app_name": phrase}}

    # ---- open / launch -------------------------------------------------
    if action_words & OPEN_WORDS:

        app = _match_app(phrase)

        if app:

            return {"tool": "open_app", "arguments": {"app_name": app}}

        # A known app wins over a website: "app open spotify" launches it.
        if site and site in _app_names():

            return {"tool": "open_app", "arguments": {"app_name": _match_app(site) or site}}

        if phrase in SITES or _match_site(phrase):

            return {"tool": "open_site", "arguments": {"name": _match_site(phrase)}}

        if site:

            return {"tool": "open_site", "arguments": {"name": site}}

        if phrase and browser.site_url(phrase):

            return {"tool": "open_site", "arguments": {"name": phrase}}

        if phrase and len(left) <= 3:

            return {"tool": "open_app", "arguments": {"app_name": phrase}}

    # ---- bare app name with a request word: "spotify chala do" --------
    if site and not action_words and any(
        word in OPEN_WORDS for word in words
    ):

        return {"tool": "open_site", "arguments": {"name": site}}

    return None
