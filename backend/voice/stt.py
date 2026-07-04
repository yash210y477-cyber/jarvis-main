from faster_whisper import WhisperModel


class SpeechToText:

    def __init__(self):

        print("Loading Whisper model...")

        self.model = WhisperModel(
            "base",
            device="cpu",
            compute_type="int8"
        )

        print("Whisper loaded.")

    def transcribe(self, audio_file):

        segments, info = self.model.transcribe(
            audio_file,
            beam_size=5
        )

        text = ""

        for segment in segments:

            text += segment.text + " "

        return text.strip()