import re


class EntityExtractor:

    """
    Extracts structured information
    from user commands.
    """

    def extract(self, text: str):

        text = text.strip()

        result = {}

        patterns = [

            (
                r"remember my name is (.+)",
                "name"
            ),

            (
                r"my name is (.+)",
                "name"
            ),

            (
                r"remember i live in (.+)",
                "city"
            ),

            (
                r"i live in (.+)",
                "city"
            ),

            (
                r"remember my email is (.+)",
                "email"
            ),

            (
                r"my email is (.+)",
                "email"
            ),

            (
                r"remember my occupation is (.+)",
                "occupation"
            ),

            (
                r"i am a[n]?\s+(.+)",
                "occupation"
            ),

            (
                r"my favourite editor is (.+)",
                "editor"
            ),

            (
                r"i use (.+)",
                "editor"
            )

        ]

        for pattern, field in patterns:

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                result["field"] = field

                result["value"] = match.group(1).strip()

                return result

        return result