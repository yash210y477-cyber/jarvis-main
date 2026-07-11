import re


class EntityExtractor:

    def extract(self, text: str):

        text = text.strip()

        patterns = [

            (r"(?:remember\s+)?my name is\s+(.+)", "name"),

            (r"(?:remember\s+)?i am\s+([a-zA-Z ]+)", "occupation"),

            (r"(?:remember\s+)?i live in\s+(.+)", "city"),

            (r"(?:remember\s+)?my email is\s+(.+)", "email"),

            (r"(?:remember\s+)?my favourite editor is\s+(.+)", "editor"),

            (r"(?:remember\s+)?i use\s+(.+)", "editor")

        ]

        for pattern, field in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                value = (
                    match.group(1)
                    .strip()
                    .rstrip(".,!?")
                )

                return {

                    "field": field,

                    "value": value

                }

        return {}