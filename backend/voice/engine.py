from voice.recorder import Recorder
from voice.stt import SpeechToText
from voice.tts import TextToSpeech


class VoiceEngine:

    def __init__(self):

        self.recorder = Recorder()

        self.stt = SpeechToText()

        self.tts = TextToSpeech()

    def listen(self):

        audio = self.recorder.record()

        text = self.stt.transcribe(audio)

        return text

    def speak(self, text):

        self.tts.speak(text)