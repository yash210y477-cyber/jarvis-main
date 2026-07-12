import json
import os


class SummaryStore:

    def __init__(self):

        self.path = "data/summaries.json"

        if not os.path.exists(self.path):

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