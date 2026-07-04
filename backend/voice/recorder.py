import tempfile

import sounddevice as sd
from scipy.io.wavfile import write


class Recorder:

    def __init__(self):

        self.sample_rate = 16000

        self.channels = 1

        self.duration = 5

    def record(self):

        print("🎤 Listening...")

        audio = sd.rec(
            int(self.duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16"
        )

        sd.wait()

        temp = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )

        write(
            temp.name,
            self.sample_rate,
            audio
        )

        return temp.name