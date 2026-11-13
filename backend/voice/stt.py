import logging

import numpy as np
from faster_whisper import WhisperModel

from config.settings import settings

# Callers speak short Hinglish commands, so the decoder is nudged
# towards that vocabulary instead of guessing freely.
COMMAND_PROMPT = (
    "Jarvis, open Spotify, play a song on Spotify, search Arijit Singh "
    "on YouTube, volume up, volume down, mute, screenshot lo, "
    "time kya hai, gaana bajao, next track, pause, lock the screen."
)

logger = logging.getLogger(__name__)


class SpeechToText:

    def __init__(self):

        logger.info("Loading Faster Whisper Model...")

        self.model = WhisperModel(
            model_size_or_path=(settings.STT_MODEL or "small"),
            device="cpu",
            compute_type=(settings.STT_COMPUTE_TYPE or "int8"),
            cpu_threads=max(2, settings.STT_THREADS),
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
            beam_size=1,  # greedy: half the CPU of a beam search
            # Call noise used to turn into invented sentences; whisper's
            # own VAD and the score thresholds below drop those segments.
            # Silence is already filtered by the call VAD, so whisper
            # does not need to run its own detector over the same audio.
            vad_filter=False,
            initial_prompt=COMMAND_PROMPT,
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

# One model for the whole process: the second call must not reload it.
_SHARED = None


def shared():
    """The single Whisper instance used by every caller of this module."""

    global _SHARED

    if _SHARED is None:

        _SHARED = SpeechToText()

    return _SHARED


def warm_up() -> bool:
    """Load the model and run one pass, so the first call replies fast."""

    try:

        model = shared()

        model.transcribe(np.zeros(16000, dtype=np.float32), language="en")

        logger.info("Speech-to-text is warm.")

        return True

    except Exception as error:

        logger.warning("Speech-to-text warm-up failed: %s", error)

        return False
