import re

from brain.facts import canonical_key


FACT_PATTERNS = (
    (r"\bmy name is\s+(.+)", "name"),
    (r"\bmy city is\s+(.+)", "city"),
    (r"\bi live in\s+(.+)", "city"),
    (r"\bi(?:'m| am) from\s+(.+)", "city"),
    (r"\bmy e-?mail is\s+(.+)", "email"),
    (r"\bmy occupation is\s+(.+)", "occupation"),
    (r"\bi(?:'m| am)\s+(?:a|an)\s+(.+)", "occupation"),
    (r"\bmy favou?rite language is\s+(.+)", "favourite_language"),
    (r"\bmy favou?rite editor is\s+(.+)", "editor"),
    (r"\bi use\s+(.+)", "editor"),
    (r"\bmy bike is\s+(.+)", "bike"),
    (r"\bmy phone is\s+(.+)", "phone"),
    (r"\bmy laptop is\s+(.+)", "laptop"),
)

# "my wifi password is hunter2" -> wifi_password
GENERIC_PATTERN = r"\bmy\s+([a-z][a-z0-9 '\-]*?)\s+(?:is|are)\s+(.+)"

# Values that are small talk, not facts.
SMALL_TALK_VALUES = {
    "tired", "bored", "happy", "sad", "fine", "okay", "ok", "good",
    "great", "angry", "hungry", "sleepy", "busy", "here", "back",
    "sorry", "sure", "done", "ready", "confused", "excited",
}

CHAIN_SPLIT = re.compile(r"\s+and\s+(?:i|my|we|the|he|she)\b", re.IGNORECASE)


class EntityExtractor:

    def __init__(self):

        self.patterns = FACT_PATTERNS

    def clean(self, value) -> str:

        value = (value or "").strip()

        value = CHAIN_SPLIT.split(value)[0]

        value = re.sub(r"\s+", " ", value)

        return value.strip().strip("\"'").rstrip(".,!?;:").strip()

    def extract_all(self, text: str) -> list:

        text = (text or "").strip()

        if not text:

            return []

        found = []

        for pattern, field in self.patterns:

            match = re.search(pattern, text, re.IGNORECASE)

            if not match:

                continue

            value = self.clean(match.group(1))

            if not value or value.lower() in SMALL_TALK_VALUES:

                continue

            found.append({"field": field, "value": value})

        generic = re.search(GENERIC_PATTERN, text, re.IGNORECASE)

        if generic:

            value = self.clean(generic.group(2))

            field = canonical_key(generic.group(1))

            used_values = {item["value"].lower() for item in found}

            if (
                field
                and value
                and value.lower() not in SMALL_TALK_VALUES
                and value.lower() not in used_values
            ):

                found.append({"field": field, "value": value})

        unique = []

        seen_fields = set()

        for item in found:

            if item["field"] in seen_fields:

                continue

            seen_fields.add(item["field"])

            unique.append(item)

        return unique

    def extract(self, text: str) -> dict:

        entities = self.extract_all(text)

        return entities[0] if entities else {}
