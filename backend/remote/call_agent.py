"""Phase B: hold a real conversation on a Telegram voice call.

The audio path is:

    Telegram call  ->  48 kHz PCM frames  ->  voice activity detection
    ->  faster-whisper  ->  Brain.chat (all the desktop tools)
    ->  spoken reply clip  ->  played back into the call

py-tgcalls 3.0 exposes both halves: ``record(chat_id, RecordStream(audio=True))``
delivers the caller's audio as ``StreamFrames`` updates, and
``play(chat_id, MediaStream(file))`` sends audio back.
"""

import asyncio
import logging
import re
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

from config.settings import settings


log = logging.getLogger("jarvis.calls.agent")

# Telegram voice is 48 kHz stereo, 16-bit PCM.
SAMPLE_RATE = 48000
CHANNELS = 2
SAMPLE_WIDTH = 2
TARGET_RATE = 16000

# How the caller's speech is cut into one request.
CHUNK_SECONDS = 0.25
SILENCE_AFTER_SPEECH = 1.0
MAX_UTTERANCE_SECONDS = 12.0
MIN_UTTERANCE_SECONDS = 0.4

# Long replies would talk over the caller forever.
MAX_SPOKEN_CHARS = 600

# Whisper invents these on call noise, and acting on them is worse than
# staying quiet.
PHANTOM_PHRASES = frozenset({
    "thank you",
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "like and subscribe",
    "subtitles by",
    "you",
    "bye",
    "goodbye",
    "hmm",
    "mm",
})


# --------------------------------------------------------------------- audio


def pcm_to_float(payload: bytes, channels: int = CHANNELS) -> np.ndarray:
    """16-bit PCM bytes -> mono float32 in [-1, 1]."""

    if not payload:
        return np.zeros(0, dtype=np.float32)

    usable = len(payload) - (len(payload) % (SAMPLE_WIDTH * max(1, channels)))

    samples = np.frombuffer(
        payload[:usable], dtype=np.int16
    ).astype(np.float32) / 32768.0

    if channels and channels > 1:

        samples = samples[: samples.size - samples.size % channels]

        samples = samples.reshape(-1, channels).mean(axis=1)

    return samples


def resample(samples: np.ndarray, source_rate: int = SAMPLE_RATE,
             target_rate: int = TARGET_RATE) -> np.ndarray:

    """Cheap linear resampler: enough for 48 kHz speech down to 16 kHz."""

    if samples.size == 0 or source_rate == target_rate:
        return samples.astype(np.float32)

    length = max(1, int(round(samples.size * target_rate / source_rate)))

    if samples.size == 1:
        return np.repeat(samples.astype(np.float32), length)

    positions = np.linspace(0, samples.size - 1, length)

    return np.interp(
        positions, np.arange(samples.size), samples
    ).astype(np.float32)


def write_wav(path: Path, samples: np.ndarray, rate: int = TARGET_RATE) -> Path:

    data = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)

    with wave.open(str(path), "wb") as handle:

        handle.setnchannels(1)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(rate)
        handle.writeframes(data.tobytes())

    return path


# ----------------------------------------------------------------------- tts


def speak_clip(text: str) -> Path | None:
    """Windows SAPI sentence -> temporary WAV file."""

    message = (text or "").strip()

    if not message:
        return None

    handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)

    path = Path(handle.name)

    handle.close()

    try:

        import comtypes
        import comtypes.client

        comtypes.CoInitialize()

        stream = comtypes.client.CreateObject("SAPI.SpFileStream")

        stream.Open(str(path), 3, False)

        voice = comtypes.client.CreateObject("SAPI.SpVoice")

        voice.AudioOutputStream = stream

        voice.Speak(message)

        stream.Close()

        if path.exists() and path.stat().st_size > 44:
            return path

    except Exception as error:

        log.warning("SAPI clip failed: %s", error)

    try:
        path.unlink()
    except OSError:
        pass

    return None


def clip_duration(path: Path) -> float:

    try:

        if str(path).lower().endswith(".wav"):

            with wave.open(str(path), "rb") as handle:

                rate = handle.getframerate() or TARGET_RATE

                return handle.getnframes() / float(rate)

    except Exception:

        pass

    try:

        import av

        with av.open(str(path)) as container:

            if container.duration:

                return float(container.duration) / 1_000_000

    except Exception:

        pass

    return 3.0


def clean_for_speech(text: str) -> str:

    text = (text or "").strip()

    if not text:
        return ""

    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)

    text = re.sub(r"[*_`#>]", "", text)

    text = re.sub(r"^\s*[-•]\s*", "", text, flags=re.MULTILINE)

    text = re.sub(r"https?://\S+", "link", text)

    text = re.sub(r"\s+", " ", text).strip()

    if len(text) > MAX_SPOKEN_CHARS:

        cut = text[:MAX_SPOKEN_CHARS]

        end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))

        text = cut if end < 80 else cut[: end + 1]

    return text


# ---------------------------------------------------------------- conversation


class CallConversation:
    """One private call: listen, understand, answer, repeat."""

    def __init__(self, calls, brain=None, chat_id=None, channels: int = CHANNELS,
                 is_active=None):

        self.calls = calls
        self.brain = brain
        self.chat_id = chat_id
        self.channels = channels
        # A dropped call must never be re-dialled: pytgcalls starts an
        # outgoing call when play/record is used outside a live call.
        self.is_active = is_active or (lambda: True)

        self.chunk_bytes = int(
            SAMPLE_RATE * CHUNK_SECONDS * SAMPLE_WIDTH * channels
        )

        self._raw = bytearray()
        self._utterance = bytearray()
        self._speech_started = False
        self._silence = 0.0
        self._utterance_started = 0.0

        self._vad = None
        self._stt = None

        self.listening = False
        self.speaking = False
        self.turns = 0
        self.received_bytes = 0
        self.peak_rms = 0.0
        self.last_heard = ""
        self.last_reply = ""
        self.last_error = ""

    # ---------------------------------------------------------------- status

    def status(self) -> dict:

        return {
            "chat_id": self.chat_id,
            "listening": self.listening,
            "speaking": self.speaking,
            "turns": self.turns,
            "input_seconds": round(self.received_bytes / float(
                SAMPLE_RATE * SAMPLE_WIDTH * self.channels
            ), 1),
            "peak_rms": round(self.peak_rms, 4),
            "last_heard": self.last_heard,
            "last_reply": self.last_reply,
            "last_error": self.last_error,
        }

    # --------------------------------------------------------------- engines

    def _engine(self):
        """Whisper + silero are heavy, so they load on the first call only."""

        if self._stt is None:

            try:

                from voice.stt import SpeechToText

                self._stt = SpeechToText()

            except Exception as error:

                self.last_error = f"Speech-to-text unavailable: {error}"
                log.warning(self.last_error)

        if self._vad is None:

            try:

                from voice.vad import VoiceActivityDetector

                self._vad = VoiceActivityDetector()

            except Exception as error:

                log.warning("VAD unavailable, using a volume gate: %s", error)

                self._vad = False

        return self._stt

    def _has_speech(self, mono: np.ndarray) -> bool:

        if mono.size == 0:
            return False

        rms = float(np.sqrt(np.mean(mono ** 2)))

        self.peak_rms = max(self.peak_rms, rms)

        if self._vad:

            try:

                import torch

                if bool(self._vad.has_speech(torch.from_numpy(mono))):

                    return True

            except Exception as error:

                log.debug("VAD check failed: %s", error)

        # Loud audio is speech even when the detector is unsure.
        return rms > (0.012 if not self._vad else 0.06)

    # ------------------------------------------------------------- listening

    async def start(self) -> dict:

        await asyncio.to_thread(self._engine)

        await self.resume_listening()

        return self.status()

    async def resume_listening(self) -> None:

        from pytgcalls.types import RecordStream

        if not self.is_active():

            self.listening = False

            return

        await self.calls.record(self.chat_id, RecordStream(audio=True))

        self._raw.clear()
        self._utterance.clear()
        self._speech_started = False
        self._silence = 0.0
        self.listening = True

    def reset(self) -> None:

        self._raw.clear()
        self._utterance.clear()
        self._speech_started = False
        self._silence = 0.0

    def feed(self, payload: bytes):
        """Add caller audio; return any complete utterances (raw PCM)."""

        if not payload or self.speaking:
            return []

        self.received_bytes += len(payload)

        self._raw.extend(payload)

        finished = []

        while len(self._raw) >= self.chunk_bytes:

            chunk = bytes(self._raw[: self.chunk_bytes])

            del self._raw[: self.chunk_bytes]

            utterance = self._consume(chunk)

            if utterance:
                finished.append(utterance)

        return finished

    def _consume(self, chunk: bytes):

        mono = resample(pcm_to_float(chunk, self.channels))

        if self._has_speech(mono):

            if not self._speech_started:

                self._speech_started = True
                self._utterance_started = time.monotonic()

            self._silence = 0.0
            self._utterance.extend(chunk)

        elif self._speech_started:

            self._silence += CHUNK_SECONDS
            self._utterance.extend(chunk)

            too_long = (
                time.monotonic() - self._utterance_started
            ) > MAX_UTTERANCE_SECONDS

            if self._silence >= SILENCE_AFTER_SPEECH or too_long:

                return self._take_utterance()

        return None

    def _take_utterance(self):

        payload = bytes(self._utterance)

        self.reset()

        seconds = len(payload) / float(
            SAMPLE_RATE * SAMPLE_WIDTH * self.channels
        )

        if seconds < MIN_UTTERANCE_SECONDS:
            return None

        return payload

    # ------------------------------------------------------------- answering

    async def handle(self, payload: bytes) -> dict:

        try:

            text = await asyncio.to_thread(self._transcribe, payload)

            if not text:

                log.info("Caller audio was not understood; still listening.")

                return {"success": False, "error": "nothing understood"}

            self.last_heard = text

            reply = await asyncio.to_thread(self._think, text)

            if not reply:

                reply = "Kuch samajh nahi aaya, phir se boliye."

            self.last_reply = reply
            self.turns += 1

            await self.say(reply)

            return {"success": True, "heard": text, "reply": reply}

        except Exception as error:

            self.last_error = str(error)
            log.warning("Call turn failed: %s", error)

            return {"success": False, "error": str(error)}

    def _transcribe(self, payload: bytes) -> str:

        stt = self._engine()

        if stt is None:
            return ""

        samples = resample(pcm_to_float(payload, self.channels))

        language = (settings.TELEGRAM_CALL_LANGUAGE or "auto").strip()

        language = None if language.lower() in ("auto", "", "none") else language

        text = ""

        try:

            text = (stt.transcribe(samples, language=language) or "").strip()

        except Exception as error:

            log.warning("Transcription failed: %s", error)

        if not text:

            # Sometimes the call carries mono audio; try that layout too.
            try:

                text = (
                    stt.transcribe(
                        resample(pcm_to_float(payload, 1)), language=language
                    )
                    or ""
                ).strip()

            except Exception as error:

                log.debug("Mono retry failed: %s", error)

        cleaned = text.strip().strip(".!?,").lower()

        if cleaned in PHANTOM_PHRASES or not any(
            character.isalpha() for character in cleaned
        ):

            return ""

        return text

    def _think(self, text: str) -> str:

        if self.brain is None:

            return "My brain is not attached to this call yet."

        message = text

        if not message.lower().startswith(("jarvis", "jarvis,")):

            message = f"jarvis {message}"

        try:

            result = self.brain.chat(message)

        except Exception as error:

            log.warning("Brain failed on a call: %s", error)

            self.last_error = str(error)

            return "Sorry, I hit an error while handling that."

        from brain.brain import FALLBACK_REPLY

        answer = result.get("response") or ""

        if answer.strip() == FALLBACK_REPLY:

            return "Ye mujhe samajh nahi aaya. Zara phir se boliye."

        return clean_for_speech(answer)

    async def say(self, text: str) -> dict:

        """Speak one reply into the call and go back to listening."""

        from pytgcalls.types import MediaStream

        message = clean_for_speech(text)

        if not message:

            return {"success": False, "error": "Nothing to say."}

        if not self.is_active():

            self.last_error = "The call ended before the reply."

            return {"success": False, "error": self.last_error}

        self.speaking = True

        self.listening = False

        self.reset()

        path = None

        try:

            path = await asyncio.to_thread(speak_clip, message)

            if path is None:

                return {"success": False, "error": "No voice available."}

            await self.calls.play(self.chat_id, MediaStream(path))

            await asyncio.sleep(clip_duration(path) + 0.35)

            return {"success": True, "spoken": message}

        except Exception as error:

            self.last_error = str(error)
            log.warning("Speaking into the call failed: %s", error)

            return {"success": False, "error": str(error)}

        finally:

            self.speaking = False

            if path is not None:

                try:
                    path.unlink()
                except OSError:
                    pass

            try:

                await self.resume_listening()

            except Exception as error:

                self.listening = False
                self.last_error = str(error)
                log.warning("Could not resume listening: %s", error)
