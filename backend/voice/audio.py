import numpy as np


class AudioProcessor:

    def __init__(self):

        self.target_rms = 0.08
        self.max_gain = 4.0

    def process(self, audio):

        if audio is None:
            return None

        audio = np.asarray(
            audio,
            dtype=np.float32
        )

        if audio.size == 0:
            return audio

        # ---------------------------------
        # Remove DC offset
        # ---------------------------------

        audio = audio - np.mean(audio)

        # ---------------------------------
        # Simple noise gate
        # ---------------------------------

        noise_level = np.percentile(
            np.abs(audio),
            20
        )

        threshold = max(
            noise_level * 2.0,
            0.008
        )

        mask = np.abs(audio) < threshold

        audio[mask] = 0

        # ---------------------------------
        # Automatic Gain Control
        # ---------------------------------

        rms = np.sqrt(
            np.mean(audio ** 2)
        )

        if rms > 0:

            gain = self.target_rms / rms

            gain = min(
                gain,
                self.max_gain
            )

            audio *= gain

        # ---------------------------------
        # Prevent clipping
        # ---------------------------------

        audio = np.clip(
            audio,
            -1.0,
            1.0
        )

        return audio