import logging
import tempfile
import wave

import numpy as np
import sounddevice as sd
import torch

from voice.vad import VoiceActivityDetector
from voice.audio import AudioProcessor


logger = logging.getLogger(__name__)


class Recorder:

    def __init__(self):

        self.sample_rate = 16000
        self.channels = 1

        # 250 ms audio chunks
        self.chunk_duration = 0.25

        # Maximum recording duration
        self.max_duration = 10

        # Stop after this much silence
        # once speech has started
        self.silence_after_speech = 1.0

        self.stop_requested = False

        # Voice Activity Detection
        self.vad = VoiceActivityDetector()

        # Noise reduction + AGC
        self.audio_processor = AudioProcessor()

    def stop(self):

        self.stop_requested = True

    def record(self):

        self.stop_requested = False

        logger.info("🎤 Listening...")

        frames = []

        speech_detected = False
        silence_time = 0.0

        samples_per_chunk = int(
            self.sample_rate * self.chunk_duration
        )

        total_chunks = int(
            self.max_duration / self.chunk_duration
        )

        for _ in range(total_chunks):

            # -----------------------------
            # STOP CHECK
            # -----------------------------

            if self.stop_requested:

                logger.info(
                    "🛑 Recording cancelled."
                )

                return None

            # -----------------------------
            # RECORD CHUNK
            # -----------------------------

            try:

                audio = sd.rec(
                    samples_per_chunk,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype="int16"
                )

                sd.wait()

            except Exception as e:

                logger.error(
                    f"Microphone Error: {e}"
                )

                return None

            # -----------------------------
            # STOP CHECK AFTER RECORDING
            # -----------------------------

            if self.stop_requested:

                logger.info(
                    "🛑 Recording cancelled."
                )

                return None

            frames.append(audio.copy())

            # -----------------------------
            # CONVERT FOR VAD
            # -----------------------------

            vad_audio = (
                audio.flatten()
                .astype(np.float32)
                / 32768.0
            )

            waveform = torch.from_numpy(
                vad_audio
            )

            # -----------------------------
            # VOICE ACTIVITY DETECTION
            # -----------------------------

            try:

                has_speech = self.vad.has_speech(
                    waveform
                )

            except Exception as e:

                logger.error(
                    f"VAD Error: {e}"
                )

                has_speech = False

            # -----------------------------
            # SPEECH DETECTED
            # -----------------------------

            if has_speech:

                if not speech_detected:

                    logger.info(
                        "🗣️ Speech detected"
                    )

                speech_detected = True

                silence_time = 0.0

            # -----------------------------
            # SILENCE DETECTED
            # -----------------------------

            else:

                if speech_detected:

                    silence_time += (
                        self.chunk_duration
                    )

                    if (
                        silence_time
                        >= self.silence_after_speech
                    ):

                        logger.info(
                            "🤫 Silence detected"
                        )

                        break

        # -----------------------------
        # NO SPEECH
        # -----------------------------

        if not speech_detected:

            logger.info(
                "🔇 No speech detected"
            )

            return None

        # -----------------------------
        # COMBINE AUDIO
        # -----------------------------

        audio = np.concatenate(
            frames,
            axis=0
        )

        # -----------------------------
        # AUDIO PROCESSING
        # Noise reduction + AGC
        # -----------------------------

        audio_float = (
            audio.flatten()
            .astype(np.float32)
            / 32768.0
        )

        audio_float = (
            self.audio_processor.process(
                audio_float
            )
        )

        if audio_float is None:

            return None

        # -----------------------------
        # CLIP AUDIO
        # -----------------------------

        audio_float = np.clip(
            audio_float,
            -1.0,
            1.0
        )

        # -----------------------------
        # BACK TO INT16
        # -----------------------------

        audio_int16 = (
            audio_float * 32767
        ).astype(np.int16)

        # -----------------------------
        # SAVE WAV
        # -----------------------------

        temp = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        )

        with wave.open(
            temp.name,
            "wb"
        ) as wf:

            wf.setnchannels(
                self.channels
            )

            wf.setsampwidth(2)

            wf.setframerate(
                self.sample_rate
            )

            wf.writeframes(
                audio_int16.tobytes()
            )

        logger.info(
            "✅ Recording Complete"
        )

        return temp.name