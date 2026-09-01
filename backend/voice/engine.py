import threading

from voice.recorder import Recorder
from voice.stt import SpeechToText
from voice.tts import TextToSpeech


class Engine:

    def __init__(self):

        self.recorder = Recorder()
        self.stt = SpeechToText()
        self.tts = TextToSpeech()

        self.speaking = False
        self.speak_lock = threading.Lock()

    # ---------------------------------
    # LISTEN
    # ---------------------------------

    def listen(self):

        try:

            # Don't listen while Jarvis is speaking
            if self.speaking:
                return None

            audio = self.recorder.record()

            if not audio:
                return None

            return audio

        except Exception as e:

            print("Listen Error:", e)

            return None

    # ---------------------------------
    # TRANSCRIBE
    # ---------------------------------

    def transcribe(self, audio):

        try:

            if not audio:
                return ""

            return self.stt.transcribe(audio)

        except Exception as e:

            print("STT Error:", e)

            return ""

    # ---------------------------------
    # SPEAK
    # ---------------------------------

    def speak(self, text):

        if not text:
            return

        with self.speak_lock:

            try:

                self.speaking = True

                self.tts.speak(text)

            except Exception as e:

                print("TTS Error:", e)

            finally:

                self.speaking = False

    # ---------------------------------
    # INTERRUPT TTS
    # ---------------------------------

    def stop_speaking(self):

        try:

            self.tts.stop()

        except Exception as e:

            print(
                "TTS Stop Error:",
                e
            )

        finally:

            self.speaking = False

    # ---------------------------------
    # STOP RECORDING
    # ---------------------------------

    def stop(self):

        try:

            self.recorder.stop()

        except Exception as e:

            print(
                "Recorder Stop Error:",
                e
            )

        self.stop_speaking()