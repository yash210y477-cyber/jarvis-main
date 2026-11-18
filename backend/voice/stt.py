"""Speech to text that hears Hindi and Hinglish, not just English.

An English-only model (base.en) turned Hindi speech into invented English
("kholo suba sart bajhe mujhe kutadina"), so the multilingual model is used and
the language is detected per clip. Hindi comes back in Devanagari, which the
rest of Jarvis cannot match against its Hinglish words, so the transcript is
written the way people type it in chat.
"""

import logging
import re
from collections import Counter

import numpy as np

from config.settings import settings
from voice import speech

# Callers speak short Hinglish commands, so the decoder is nudged
# towards that vocabulary instead of guessing freely.
COMMAND_PROMPT = (
    "Jarvis, open Spotify, play a song on Spotify, search Arijit Singh "
    "on YouTube, volume up, volume down, mute, screenshot lo, "
    "time kya hai, gaana bajao, screen band karo, next track, pause, "
    "lock the screen, mujhe kya karna hai, bhej do, kholo."
)

DEVANAGARI = re.compile(r"[\u0900-\u097F]")

REPEATED_CHAR = re.compile(r"(\S)\1{4,}")
REPEATED_WORD = re.compile(r"\b(\S+)(?:\s+\1){3,}\b", re.IGNORECASE)

logger = logging.getLogger(__name__)


def model_name() -> str:
    """The multilingual model, even when the config names an English-only one."""

    name = (settings.STT_MODEL or "small").strip()

    # base.en / small.en / medium.en hear only English.
    if name.endswith(".en"):
        name = name[:-3]

    return name or "small"


def resolve_language(language=None) -> str | None:
    """None means "detect it", which is what Hindi and Hinglish need."""

    wanted = (language if language is not None else settings.STT_LANGUAGE) or "auto"
    wanted = str(wanted).strip().lower()

    if wanted in ("", "auto", "none", "detect"):
        return None

    return wanted


def repetitive(text: str) -> bool:
    """True for a hallucinated line such as \"om om om om\" or \"aaaaaaaa\"."""

    sample = (text or "").strip()

    if len(sample) < 8:
        return False

    return bool(REPEATED_CHAR.search(sample) or REPEATED_WORD.search(sample))


def looks_broken(text: str) -> bool:
    """A decoder loop, not speech: almost no variety in the characters."""

    sample = (text or "").strip()

    if not sample:
        return True

    if repetitive(sample):
        return True

    letters = [char for char in sample if not char.isspace()]

    if len(letters) < 20:
        return False

    if len(set(letters)) / len(letters) < 0.25:
        return True

    return max(Counter(letters).values()) / len(letters) > 0.35


class SpeechToText:

    def __init__(self):

        # The model is a download and a few hundred megabytes of weights; it is
        # opened when the first clip is transcribed, not when Jarvis starts.
        from faster_whisper import WhisperModel

        self.name = model_name()

        logger.info("Loading Faster Whisper Model (%s)...", self.name)

        self.model = WhisperModel(
            model_size_or_path=self.name,
            device="cpu",
            compute_type=(settings.STT_COMPUTE_TYPE or "int8"),
            cpu_threads=max(2, settings.STT_THREADS),
            num_workers=2,
        )

        logger.info("Whisper Model Loaded Successfully.")

        self.last_language = None

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

    def detect_language(self, samples):
        """The spoken language, or None when the detector is unsure."""

        try:

            found, probability, _ = self.model.detect_language(samples)

            logger.info("Detected %s (%.2f)", found, probability)

            return found if probability >= 0.4 else None

        except Exception as error:

            logger.warning("Language detection failed: %s", error)

            return None

    def _decode(self, audio, language, prompt, repetition_penalty=1.0):
        """One decoder pass; returns the joined text of the kept segments."""

        segments, info = self.model.transcribe(
            audio,
            language=language,
            beam_size=1,  # greedy: half the CPU of a beam search
            # Call noise used to turn into invented sentences; whisper's
            # own VAD and the score thresholds below drop those segments.
            # Silence is already filtered by the call VAD, so whisper
            # does not need to run its own detector over the same audio.
            vad_filter=False,
            # Nothing reads the timestamps, and asking for them slows the
            # decoder down on CPU.
            without_timestamps=True,
            initial_prompt=prompt,
            condition_on_previous_text=False,
            temperature=0,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4,
            repetition_penalty=repetition_penalty,
        )

        self.last_language = getattr(info, "language", language)

        parts = []

        for segment in segments:

            if segment.no_speech_prob > 0.6:

                continue

            if segment.avg_logprob < -1.0:

                continue

            if repetitive(segment.text):

                logger.info("Dropped a repeated segment: %r", segment.text[:40])

                continue

            parts.append(segment.text.strip())

        return " ".join(parts).strip()

    def transcribe(self, audio, language=None):

        logger.info("Transcribing Audio...")

        # Call audio arrives as float32 samples, mic recordings as a path.
        if isinstance(audio, np.ndarray):

            audio = np.ascontiguousarray(audio, dtype=np.float32)
        else:

            from faster_whisper.audio import decode_audio

            audio = decode_audio(audio, sampling_rate=16000)

        language = resolve_language(language)

        # Pass a concrete language: transcribe(language=None) re-detects on every
        # segment, which measured slower than one detection pass here.
        if language is None:

            language = self.detect_language(audio)

        # The Hinglish prompt keeps the transcript in Latin letters, but on
        # some clips it makes the decoder loop ("om om om"). A retry without
        # it gets the plain Hindi words.
        text = self._decode(audio, language, COMMAND_PROMPT)

        if looks_broken(text):

            logger.info("Decode looked broken (%r); retrying plainly.", text[:40])

            retry = self._decode(audio, language, None, repetition_penalty=1.15)

            if not looks_broken(retry) or not text:

                text = retry

        if DEVANAGARI.search(text):

            text = speech.to_hinglish(text)

        text = self.clean_text(text)

        logger.info("Recognized: %s", text)

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
