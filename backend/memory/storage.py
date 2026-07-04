import json
from pathlib import Path


class Storage:
    """
    Handles all file operations for JARVIS memory.

    NOTE:
    No other module should directly read/write memory.json.
    """

    def __init__(self):

        self.base_dir = Path(__file__).resolve().parent.parent

        self.data_dir = self.base_dir / "data"

        self.memory_file = self.data_dir / "memory.json"

        self.initialize()

    def initialize(self):

        self.data_dir.mkdir(parents=True, exist_ok=True)

        if not self.memory_file.exists():

            default_memory = {

                "profile": {
                    "name": "",
                    "email": "",
                    "city": "",
                    "occupation": ""
                },

                "preferences": {
                    "theme": "dark",
                    "browser": "chrome",
                    "editor": "VS Code"
                },

                "facts": [],

                "conversation": []

            }

            with open(
                self.memory_file,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    default_memory,
                    file,
                    indent=4
                )

    def read(self):

        with open(
            self.memory_file,
            "r",
            encoding="utf-8"
        ) as file:

            return json.load(file)

    def write(self, data):

        with open(
            self.memory_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                data,
                file,
                indent=4
            )

    def reset(self):

        if self.memory_file.exists():

            self.memory_file.unlink()

        self.initialize()