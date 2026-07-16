import logging

from faster_whisper import WhisperModel


logger = logging.getLogger(__name__)


class SpeechToText:

    def __init__(self):

        self.model = None

    def load_model(self):

        if self.model is None:

            logger.info("Loading Whisper model...")

            self.model = WhisperModel(

                "base",

                device="cpu",

                compute_type="int8"

            )

            logger.info("Whisper loaded.")

    def transcribe(self, audio_file):

        self.load_model()

        segments, info = self.model.transcribe(

            audio_file,

            beam_size=5

        )

        text = ""

        for segment in segments:

            text += segment.text + " "

        return text.strip()