from voice.engine import VoiceEngine
from controllers.command_controller import CommandController


class VoiceController:

    def __init__(self):

        self.voice = VoiceEngine()

        self.command = CommandController()

    def start(self):

        print("\n🎤 Listening...\n")

        text = self.voice.listen()

        print(f"You : {text}")

        response = self.command.execute(text)

        print()

        print(response)

        if response.get("message"):

            self.voice.speak(response["message"])