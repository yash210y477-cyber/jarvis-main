from brain.brain import Brain


class CommandController:

    def __init__(self):
        self.brain = Brain()

    def execute(self, text: str):
        return self.brain.process(text)