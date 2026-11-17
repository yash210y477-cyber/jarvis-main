import json
import os

from memory.storage import data_dir


class SummaryStore:

    def __init__(self):

        # Same data folder as the rest of the memory, so a checkout without a
        # seeded backend/data directory (CI, a fresh clone) still starts.
        self.path = data_dir() / "summaries.json"

        if not os.path.exists(self.path):

            self.path.parent.mkdir(parents=True, exist_ok=True)

            with open(
                self.path,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    {
                        "summary": ""
                    },
                    f,
                    indent=4,
                    ensure_ascii=False
                )

    def load(self):

        with open(
            self.path,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    def latest(self):

        data = self.load()

        return data.get("summary", "")

    def save(self, summary: str):

        with open(
            self.path,
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(

                {

                    "summary": summary

                },

                f,

                indent=4,

                ensure_ascii=False

            )

    def clear(self):

        self.save("")