"""
Local replies for everyday messages.

Greetings, thanks, time and "who are you" must never depend on an AI provider
or an API key: they are answered here, before any network call.
"""

import datetime
import re

GREETINGS = (
    "hi",
    "hii",
    "hiya",
    "hey",
    "heyy",
    "hello",
    "helo",
    "yo",
    "hola",
    "namaste",
    "salam",
    "assalamualaikum",
    "good morning",
    "good afternoon",
    "good evening",
    "morning",
    "evening",
)

GREETING_WORDS = r"(?:hi|hii|hiya|hey|heyy|hello|helo|yo|hola)"

HOW_ARE_YOU = (
    r"how are you",
    r"how r u",
    r"how're you",
    r"how is it going",
    r"how's it going",
    r"what'?s up",
    r"whats up",
    r"sup\\b",
)

THANKS = (r"thanks", r"thank you", r"thx", r"ty\\b", r"shukriya", r"dhanyawad")

BYE = (r"bye", r"goodbye", r"good night", r"goodnight", r"see you", r"see ya")

ACK = (
    r"ok",
    r"okay",
    r"k",
    r"cool",
    r"nice",
    r"great",
    r"awesome",
    r"perfect",
    r"hmm+",
    r"yeah",
    r"yes",
    r"no",
)

CAPABILITIES = """I can:
- remember things you tell me ("my favourite colour is black")
- answer them back ("what is my favourite colour?")
- open and close desktop apps ("open chrome")
- report CPU, RAM, storage and network
- search the web and open sites
- chat with you when an AI provider is configured"""


def _greeting() -> str:

    hour = datetime.datetime.now().hour

    if hour < 5:
        return "Good night"
    if hour < 12:
        return "Good morning"
    if hour < 17:
        return "Good afternoon"
    if hour < 21:
        return "Good evening"
    return "Good night"


def _matches(text: str, patterns) -> bool:

    return any(re.fullmatch(pattern, text) for pattern in patterns)


TIME_PHRASES = (
    "what is the time",
    "what's the time",
    "whats the time",
    "what time is it",
    "what is the clock",
    "tell me the time",
    "current time",
    "time now",
    "time please",
    "got the time",
    "kitna time",
    "kitne baje",
    "time kya",
    "what is time",
    "whats time",
    "time bata",
    "samay kya",
)

DATE_PHRASES = (
    "what is the date",
    "what's the date",
    "whats the date",
    "what is the day",
    "what day is it",
    "what day is today",
    "today's date",
    "todays date",
    "which day",
    "which date",
    "current date",
    "aaj ki date",
    "aaj ki tareekh",
    "aaj kaunsi date",
    "today date",
    "date today",
    "what is today date",
    "aaj date",
)


QUESTION_WORDS = {
    "what", "whats", "what's", "which", "kya", "kaunsi", "bata", "batao",
    "tell", "current", "now", "abhi", "kitna", "kitne", "hai", "is",
}


def _words(text: str) -> set:
    return set(re.findall(r"[a-z']+", text))


def _is_time_query(text: str) -> bool:

    if any(phrase in text for phrase in TIME_PHRASES):
        return True

    words = _words(text)

    return bool(words & {"time", "baje", "samay"}) and bool(words & QUESTION_WORDS)


def _is_date_query(text: str) -> bool:

    if any(phrase in text for phrase in DATE_PHRASES):
        return True

    words = _words(text)

    return bool(words & {"date", "tareekh", "din"}) and bool(words & QUESTION_WORDS)

def local_reply(text: str, memory=None) -> str:
    """
    Return a reply for a normal, everyday message, or "" when the message
    needs a real AI answer.
    """

    lowered = (text or "").strip().lower()

    lowered = re.sub(r"[!?.,]+$", "", lowered).strip()

    if not lowered:
        return ""

    name = ""

    if memory is not None:
        try:
            name = (memory.get_profile() or {}).get("name") or ""
        except Exception:
            name = ""

    who = f" {name}" if name else ""

    # "hey", "hi jarvis", "good morning jarvis"
    stripped = re.sub(r"\bjarvis\b", "", lowered).strip()

    stripped = re.sub(r"\s+", " ", stripped)

    if stripped in GREETINGS:
        return f"{_greeting()}{who} 👋 How can I help?"

    if re.fullmatch(rf"{GREETING_WORDS}(\s+there)?", stripped):
        return f"{_greeting()}{who} 👋 I'm here — what do you need?"

    if _matches(lowered, HOW_ARE_YOU):
        return "Running smoothly, thanks for asking. What can I do for you?"

    if _matches(lowered, THANKS) or lowered.startswith("thank you"):
        return "Anytime. Anything else?"

    if _matches(lowered, BYE):
        return f"See you{who}. I'll be right here."

    if lowered in ("who are you", "what is your name", "whats your name",
                   "what's your name", "introduce yourself", "your name"):
        return (
            "I'm JARVIS — your local AI assistant. I keep your memory on this "
            "machine, control your apps and report on your system."
        )

    if lowered in ("what can you do", "help", "commands", "what can you do?"):
        return CAPABILITIES

    if _is_time_query(lowered):

        return "It's " + datetime.datetime.now().strftime("%I:%M %p").lstrip("0") + "."

    if _is_date_query(lowered):

        return "Today is " + datetime.datetime.now().strftime("%A, %d %B %Y") + "."

    if re.search(r"\bare you\s+(?:there|online|awake)\b", lowered):
        return "I'm here. What do you need?"

    if re.search(r"\b(good job|well done|nice work|great work|love you)\b", lowered):
        return "Thank you — happy to help."

    if _matches(lowered, ACK):
        return "Noted."

    return ""
