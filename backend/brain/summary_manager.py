from memory.summary import SummaryStore
from providers.summarizer import Summarizer


class SummaryManager:

    def __init__(self):

        self.store = SummaryStore()

        self.ai = Summarizer()

    def generate(self, messages):

        previous = self.store.latest()

        conversation = []

        if previous:

            conversation.append({

                "role": "system",

                "text": f"Previous Summary:\n{previous}"

            })

        conversation.extend(messages)

        summary = self.ai.summarize(conversation)

        if summary:

            self.store.save(summary)

        return summary

    def latest(self):

        return self.store.latest()

    def clear(self):

        self.store.clear()