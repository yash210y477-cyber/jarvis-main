from providers.manager import AIManager


class Summarizer:

    def __init__(self):

        self.ai = AIManager()

    def summarize(self, messages):

        if not messages:

            return ""

        conversation = []

        for msg in messages:

            role = msg["role"].capitalize()

            text = msg["text"]

            conversation.append(

                f"{role}: {text}"

            )

        prompt = f"""
Summarize the following conversation.

Rules:

- Maximum 10 bullet points.
- Keep important facts.
- Keep user preferences.
- Keep project progress.
- Ignore greetings.
- Return only the summary.

Conversation:

{chr(10).join(conversation)}
"""

        result = self.ai.chat(prompt)

        if result["success"]:

            return result["response"]

        return ""