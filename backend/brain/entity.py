import re


class EntityExtractor:

    def __init__(self):

        self.patterns = [

            (r"(?:remember\s+)?my name is\s+(.+)", "name"),

            (r"(?:remember\s+)?i live in\s+(.+)", "city"),

            (r"(?:remember\s+)?my city is\s+(.+)", "city"),

            (r"(?:remember\s+)?my email is\s+(.+)", "email"),

            (r"(?:remember\s+)?i am\s+(?:a|an)?\s*(.+)", "occupation"),

            (r"(?:remember\s+)?my occupation is\s+(.+)", "occupation"),

            (r"(?:remember\s+)?my favourite language is\s+(.+)", "favourite_language"),

            (r"(?:remember\s+)?my favorite language is\s+(.+)", "favourite_language"),

            (r"(?:remember\s+)?my favourite editor is\s+(.+)", "editor"),

            (r"(?:remember\s+)?my favorite editor is\s+(.+)", "editor"),

            (r"(?:remember\s+)?i use\s+(.+)", "editor"),

            (r"(?:remember\s+)?my bike is\s+(.+)", "bike"),

            (r"(?:remember\s+)?my phone is\s+(.+)", "phone"),

            (r"(?:remember\s+)?my laptop is\s+(.+)", "laptop"),

        ]

    def clean(self, value):

        return (

            value.strip()

            .rstrip(".,!?")

        )

    def extract(self, text):

        for pattern, field in self.patterns:

            match = re.search(

                pattern,

                text,

                re.IGNORECASE

            )

            if match:

                return {

                    "field": field,

                    "value": self.clean(

                        match.group(1)

                    )

                }

        return {}