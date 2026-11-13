import logging

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


class SpeechToText:

    def __init__(self):

        logger.info("Loading Faster Whisper Model...")

        self.model = WhisperModel(
            model_size_or_path="base",
            device="cpu",
            compute_type="int8",
            cpu_threads=4,
            num_workers=2,
        )

        logger.info("Whisper Model Loaded Successfully.")

        self.replacements = {
            "hallo": "hello",
            "helo": "hello",
            "hellow": "hello",
            "helloo": "hello",

            "jervis": "jarvis",
            "jarvice": "jarvis",
            "jarvish": "jarvis",
            "jar vis": "jarvis",

            "vs cord": "vs code",
            "vscode": "vs code",
            "visual studio": "visual studio code",

            "good morning service": "good morning jarvis",
            "good morning jervis": "good morning jarvis",
        }

    def clean_text(self, text: str):

        text = text.lower().strip()

        for wrong, correct in self.replacements.items():
            text = text.replace(wrong, correct)

        return text

    def transcribe(self, audio, language="en"):

        logger.info("Transcribing Audio...")

        # Call audio arrives as float32 samples, mic recordings as a path.
        if isinstance(audio, np.ndarray):

            audio = np.ascontiguousarray(audio, dtype=np.float32)

        segments, info = self.model.transcribe(
            audio,
            language=language,
            beam_size=2,
            # Call noise used to turn into invented sentences; whisper's
            # own VAD and the score thresholds below drop those segments.
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
            condition_on_previous_text=False,
            temperature=0,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
        )

        parts = []

        for segment in segments:

            if segment.no_speech_prob > 0.6:

                continue

            if segment.avg_logprob < -1.0:

                continue

            parts.append(segment.text.strip())

        text = " ".join(parts)

        text = self.clean_text(text)

        logger.info(f"Recognized: {text}")

        return text