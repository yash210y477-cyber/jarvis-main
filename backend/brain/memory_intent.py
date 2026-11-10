"""
Memory intents: save and recall personal facts without any AI provider.

"my favourite colour is black" must be stored immediately, and
"what is my city name" must answer the city (not the name).
"""

import re

from brain.facts import canonical_key, human_key

PROFILE_KEYS = ("name", "email", "city", "occupation")

REMEMBER_THIS = re.compile(
    r"^(?:please\s+|jarvis[,\s]+)*remember(?:\s+this)?\s*[:\-]?\s+(.+)$"
)

RECALL_ALL = re.compile(
    r"^(?:what do you (?:remember|know about me)|"
    r"tell me about (?:me|myself)|"
    r"what have you remembered|"
    r"my memory|memory summary)$"
)


def normalise(text: str) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"[.!?,;]+$", "", text).strip()


def clean_value(value: str) -> str:
    value = (value or "").strip().strip("\"'")
    value = re.sub(r"\s+", " ", value)
    return value.rstrip(".!?,;").strip()


def detect_remember(text: str):
    """Return {"field": key, "value": v} or {"note": text} or None."""

    t = normalise(text)
    if not t:
        return None

    # remember that my favourite colour is black
    m = re.match(
        r"^(?:please\s+|jarvis[,\s]+)*remember(?:\s+that)?\s+my\s+(.+?)\s+(?:is|are)\s+(.+)$",
        t,
    )
    if m:
        return {"field": canonical_key(m.group(1)), "value": clean_value(m.group(2))}

    # remember that i live in mumbai
    m = re.match(
        r"^(?:please\s+|jarvis[,\s]+)*remember(?:\s+that)?\s+i\s+(?:live|stay)\s+in\s+(.+)$",
        t,
    )
    if m:
        return {"field": "city", "value": clean_value(m.group(1))}

    # remember that <something> is <value>
    m = re.match(
        r"^(?:please\s+|jarvis[,\s]+)*remember(?:\s+that)?\s+(.+?)\s+(?:is|are)\s+(.+)$",
        t,
    )
    if m:
        return {"field": canonical_key(m.group(1)), "value": clean_value(m.group(2))}

    # remember to buy milk / remember this
    m = REMEMBER_THIS.match(t)
    if m:
        note = re.sub(r"^to\s+", "", clean_value(m.group(1)))
        return {"note": note}

    # my favourite colour is black
    m = re.match(r"^my\s+(.+?)\s+(?:is|are)\s+(.+)$", t)
    if m:
        field = canonical_key(m.group(1))
        if field:
            return {"field": field, "value": clean_value(m.group(2))}

    # my name is yash
    m = re.match(r"^(?:my\s+)?name(?:'s|\s+is)\s+(.+)$", t)
    if m:
        return {"field": "name", "value": clean_value(m.group(1))}

    # call me yash
    m = re.match(r"^call me\s+(.+)$", t)
    if m:
        return {"field": "name", "value": clean_value(m.group(1))}

    # i live in mumbai / i stay in mumbai
    m = re.match(r"^i\s+(?:live|stay)\s+in\s+(.+)$", t)
    if m:
        return {"field": "city", "value": clean_value(m.group(1))}

    # i'm from mumbai
    m = re.match(r"^i(?:'m| am)\s+from\s+(.+)$", t)
    if m:
        return {"field": "city", "value": clean_value(m.group(1))}

    # my email is a@b.com
    m = re.match(r"^my\s+e-?mail\s+(?:is|id is)\s+(.+)$", t)
    if m:
        return {"field": "email", "value": clean_value(m.group(1))}

    # i am a student / i'm a developer
    m = re.match(r"^i(?:'m| am)\s+(?:a|an)\s+(.+)$", t)
    if m:
        return {"field": "occupation", "value": clean_value(m.group(1))}

    return None


def detect_recall(text: str):
    """Return a canonical key, '__all__', or None."""

    t = normalise(text)
    if not t:
        return None

    if RECALL_ALL.match(t):
        return "__all__"

    # what is my city name / what's my favourite colour / which is my bike
    m = re.match(
        r"^(?:what|what's|whats|which|tell me)(?:\s+is|\s+was|\s+are)?\s+my\s+(.+)$",
        t,
    )
    if m:
        key = canonical_key(m.group(1))
        if key:
            return key

    # do you remember my favourite colour
    m = re.match(r"^(?:do you (?:know|remember)|can you (?:recall|tell me))\s+my\s+(.+)$", t)
    if m:
        key = canonical_key(m.group(1))
        if key:
            return key

    if re.match(r"^(?:where do i live|where i live|where am i from)$", t):
        return "city"

    if re.match(r"^(?:who am i|what do you know about me)$", t):
        return "__all__"

    return None


def describe(memory, key: str) -> str:
    """Build a natural answer for a recalled key."""

    human = human_key(key)

    profile = {}
    try:
        profile = memory.get_profile() or {}
    except Exception:
        profile = {}

    if key in profile and profile.get(key):
        return f"Your {human} is {profile[key]}."

    value = None
    try:
        value = memory.recall(key)
    except Exception:
        value = None

    if value:
        return f"Your {human} is {value}."

    # loose fallback: "city name" style leftovers, matching fact keys
    try:
        for item in memory.all_facts():
            if key and key.split("_")[0] in item.get("key", ""):
                return f"Your {human_key(item['key'])} is {item['value']}."
    except Exception:
        pass

    return f"I don't know your {human} yet. Tell me: my {human} is ..."


def describe_all(memory) -> str:
    """ChatGPT-style summary of everything remembered."""

    lines = []

    try:
        profile = memory.get_profile() or {}
        for key in PROFILE_KEYS:
            if profile.get(key):
                lines.append(f"- {human_key(key)}: {profile[key]}")
    except Exception:
        pass

    try:
        for item in memory.all_facts():
            if item.get("key") and item.get("value"):
                lines.append(f"- {human_key(item['key'])}: {item['value']}")
    except Exception:
        pass

    if not lines:
        return "I don't remember anything about you yet."

    return "Here's what I remember:\n" + "\n".join(lines)
