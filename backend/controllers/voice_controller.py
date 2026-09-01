import threading

from voice.engine import Engine
from controllers.command_controller import CommandController


class VoiceController:

    def __init__(self):

        self.engine = Engine()
        self.command = CommandController()

        self.running = False
        self.thread = None

    def _extract_reply(self, response):

        if isinstance(response, dict):

            return (
                response.get("response")
                or response.get("message")
                or response.get("reply")
                or str(response)
            )

        return str(response)

    def start(self):

        audio = self.engine.listen()

        if not audio:
            return {
                "success": False,
                "message": "No audio detected"
            }

        text = self.engine.transcribe(audio)

        if not text:
            return {
                "success": False,
                "message": "Speech not recognized"
            }

        response = self.command.execute(text)

        reply = self._extract_reply(response)

        self.engine.speak(reply)

        return {
            "success": True,
            "heard": text,
            "response": reply
        }

    def _voice_loop(self):

        print("🎤 Voice Mode Started")

        while self.running:

            try:

                audio = self.engine.listen()

                if not self.running:
                    break

                if not audio:
                    continue

                text = self.engine.transcribe(audio)

                if not text:
                    continue

                print(f"👤 You : {text}")

                if text.lower() in [
                    "stop",
                    "stop listening",
                    "exit",
                    "quit",
                    "bye",
                    "goodbye"
                ]:

                    self.stop()
                    break

                response = self.command.execute(text)

                reply = self._extract_reply(response)

                print(f"🤖 Jarvis : {reply}")

                self.engine.speak(reply)

            except Exception as e:

                print("Voice Error:", e)

        print("🛑 Voice Mode Ended")

    def start_continuous(self):

        if self.running:

            return {
                "success": True,
                "message": "Voice already running"
            }

        self.running = True

        self.thread = threading.Thread(
            target=self._voice_loop,
            daemon=True
        )

        self.thread.start()

        return {
            "success": True,
            "message": "Voice Started"
        }

    def stop(self):

        self.running = False
        self.engine.stop()

        return {
            "success": True,
            "message": "Voice Stopped"
        }