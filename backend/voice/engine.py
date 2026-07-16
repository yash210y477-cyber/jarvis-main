from voice.recorder import Recorder
from voice.stt import SpeechToText
from voice.tts import TextToSpeech


class VoiceEngine:

    _instance = None

    def __new__(cls):

        if cls._instance is None:

            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self):

        if hasattr(self, "_initialized"):

            return

        self.recorder = Recorder()

        self.stt = SpeechToText()

        self.tts = TextToSpeech()

        self._initialized = True

    def listen(self):

        audio = self.recorder.record()

        return self.stt.transcribe(audio)

    def speak(self, text):

        self.tts.speak(text)