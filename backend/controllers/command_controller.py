from brain.brain import Brain


class CommandController:

    def __init__(self):
        self.brain = Brain()

    def execute(self, text: str):

        if not text or not text.strip():
            return {
                "success": False,
                "message": "No voice detected."
            }

        try:
            return self.brain.chat(text)

        except Exception as e:

            return {
                "success": False,
                "message": str(e)
            }