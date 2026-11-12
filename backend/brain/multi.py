"""Split one line containing several commands into separate commands."""

import re


CONNECTORS = (
    " and then ",
    " uske baad ",
    " then ",
    " aur ",
    " phir ",
    " and ",
    " afterwards ",
    " ; ",
    ";",
)

COMMAND_STARTS = (
    "open", "close", "visit", "launch", "start", "minimize", "minimise",
    "show", "lock", "set", "remind", "cancel", "list", "take", "tell",
    "what", "which", "search", "run", "shut", "restart", "reboot", "sleep",
    "sign", "focus", "switch", "jump", "go", "play", "pause", "mute",
    "volume", "increase", "decrease", "notify", "screenshot", "next",
    "previous", "stop", "read", "write", "system", "kholo", "khol", "band",
)


def _is_command(part: str) -> bool:

    from brain import local_clock
    from tools import local_intents

    text = (part or "").strip().lower()

    if not text:
        return False

    if local_intents.detect(text) is not None:
        return True

    if local_clock.detect(text) is not None:
        return True

    first = text.split(" ", 1)[0].strip(",")

    return first in COMMAND_STARTS


def split_commands(message: str):

    text = (message or "").strip()

    if not text:
        return []

    for connector in CONNECTORS:

        if connector in text.lower():

            parts = [
                part.strip(" ,.")
                for part in re.split(
                    re.escape(connector), text, flags=re.IGNORECASE
                )
                if part.strip(" ,.")
            ]

            if len(parts) > 1 and all(_is_command(part) for part in parts):
                return parts

    return [text]
