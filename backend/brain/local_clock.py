"""Local date and time answers.

JARVIS must answer "what is the current month" without any API key, so the
clock is read straight from the machine and rendered here.
"""

import datetime
import re

from config.settings import settings


QUESTION_WORDS = (
    "what", "which", "when", "tell", "current", "today", "now",
    "kya", "kaun", "konsa", "bata", "abhi", "is", "hai", "bol",
)

TIME_WORDS = ("time", "baje", "samay", "clock")
DATE_WORDS = ("date", "tareekh", "aaj")
MONTH_WORDS = ("month", "mahina", "maheena", "mahine")
YEAR_WORDS = ("year", "saal", "sal")
WEEKDAY_WORDS = ("weekday", "day of week", "which day", "what day is it",
                 "what day is today", "kaun sa din", "kaunsa din")
WEEK_WORDS = ("week number", "which week", "week of the year", "hafte number")
ZONE_WORDS = ("timezone", "time zone", "tz")


def now() -> datetime.datetime:

    return datetime.datetime.now().astimezone()


def _ordinal(number: int) -> str:

    if 10 <= number % 100 <= 20:

        suffix = "th"

    else:

        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")

    return f"{number}{suffix}"


def _has_question(text: str) -> bool:

    return any(word in text.split() for word in QUESTION_WORDS)


def detect(text: str):
    """Return the kind of clock question, or None."""

    lowered = re.sub(r"[!?.,]+", " ", (text or "").strip().lower())

    lowered = re.sub(r"\s+", " ", lowered).strip()

    if not lowered:

        return None

    if any(word in lowered for word in ZONE_WORDS):

        return "timezone"

    if any(word in lowered for word in WEEK_WORDS):

        return "week"

    if any(word in lowered for word in MONTH_WORDS) and _has_question(lowered):

        return "month"

    if any(word in lowered for word in YEAR_WORDS) and _has_question(lowered):

        return "year"

    if re.search(r"\b(day|din)\b", lowered) and _has_question(lowered):

        return "weekday"

    if lowered.strip(" .") in (
        "what is today", "what's today", "whats today", "today",
        "today kya hai", "aaj kya hai",
    ):

        return "date"

    if any(word in lowered for word in WEEKDAY_WORDS):

        return "weekday"

    if any(word in lowered for word in DATE_WORDS) and (
        _has_question(lowered) or "aaj" in lowered
    ):

        return "date"

    if any(word in lowered for word in TIME_WORDS) and _has_question(lowered):

        return "time"

    return None


def render(kind: str) -> str:
    """Spoken answer for a clock question, in the configured language."""

    moment = now()

    hinglish = (getattr(settings, "JARVIS_LANGUAGE", "") or "").lower() in (
        "hinglish", "hindi", "hi",
    )

    if kind == "time":

        clock = moment.strftime("%I:%M %p").lstrip("0")

        if hinglish:

            return f"Abhi {clock} baje hain."

        return f"It's {clock} ({moment.tzname() or 'local time'})."

    if kind == "date":

        if hinglish:

            return f"Aaj {moment.strftime('%A, %d %B %Y')} hai."

        return f"Today is {moment.strftime('%A, %d %B %Y')}."

    if kind == "weekday":

        if hinglish:

            return f"Aaj {moment.strftime('%A')} hai."

        return f"Today is {moment.strftime('%A')}."

    if kind == "month":

        if hinglish:

            return f"{moment.strftime('%B')} chal raha hai."

        return (
            f"It's {moment.strftime('%B')} — the "
            f"{_ordinal(moment.month)} month of {moment.year}."
        )

    if kind == "year":

        if hinglish:

            return f"{moment.year} chal raha hai."

        return f"It's {moment.year}."

    if kind == "week":

        if hinglish:

            return f"Ye {moment.year} ka {moment.isocalendar().week}va hafta hai."

        return (
            f"This is week {moment.isocalendar().week} of {moment.year}."
        )

    if kind == "timezone":

        offset = moment.strftime("%z")

        pretty = f"UTC{offset[:3]}:{offset[3:]}" if offset else "UTC"

        if hinglish:

            return f"Tumhara timezone {moment.tzname() or 'local time'} hai ({pretty})."

        return f"Your timezone is {moment.tzname() or 'local time'} ({pretty})."

    if kind == "datetime":

        if hinglish:

            return (
                f"Abhi {moment.strftime('%I:%M %p').lstrip('0')} baje hain, "
                f"{moment.strftime('%A, %d %B %Y')} ko."
            )

        return (
            f"It's {moment.strftime('%I:%M %p').lstrip('0')} on "
            f"{moment.strftime('%A, %d %B %Y')}."
        )

    return ""

def reply(text: str):
    """Return a clock answer for the message, or None."""

    kind = detect(text)

    if not kind:

        return None

    return render(kind)
