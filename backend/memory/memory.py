import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

MEMORY_FILE = BASE_DIR / "data" / "memory.json"


class Memory:

    def __init__(self):

        self.memory = self.load()

    def load(self):

        if not MEMORY_FILE.exists():

            MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)

            MEMORY_FILE.write_text("{}")

        with open(MEMORY_FILE, "r", encoding="utf-8") as file:

            return json.load(file)

    def save(self):

        with open(MEMORY_FILE, "w", encoding="utf-8") as file:

            json.dump(
                self.memory,
                file,
                indent=4
            )

    def remember(self, text):

        key = f"memory_{len(self.memory)+1}"

        self.memory[key] = text

        self.save()

    def recall(self):

        return self.memory

    def forget(self, key):

        if key in self.memory:

            del self.memory[key]

            self.save()

            return True

        return False

    def clear(self):

        self.memory = {}

        self.save()