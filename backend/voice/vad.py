import logging

import torch
from silero_vad import load_silero_vad


log = logging.getLogger(__name__)


class VoiceActivityDetector:
    """Silero VAD over short call chunks.

    get_speech_timestamps() needs well over a quarter second of audio, so it
    reported silence for every 250 ms call chunk. The model itself works on
    512-sample windows at 16 kHz, so the windows are scored directly here.
    """

    window = 512

    def __init__(self):

        self.model = load_silero_vad()

        self.sample_rate = 16000
        self.threshold = 0.5

    def _probabilities(self, waveform):

        try:

            self.model.reset_states()

        except Exception:

            pass

        for start in range(0, waveform.numel() - self.window + 1, self.window):

            chunk = waveform[start: start + self.window]

            yield float(self.model(chunk, self.sample_rate).detach())

    def has_speech(self, audio):

        try:

            if audio is None:

                return False

            waveform = audio if isinstance(audio, torch.Tensor) else torch.tensor(audio)

            waveform = waveform.float()

            if waveform.ndim > 1:

                waveform = waveform.mean(dim=1)

            if waveform.numel() < self.window:

                return False

            scores = list(self._probabilities(waveform))

            if scores:

                return max(scores) >= self.threshold

        except Exception as error:

            log.debug("VAD error, falling back to a volume gate: %s", error)

        data = audio.detach().numpy() if isinstance(audio, torch.Tensor) else audio

        if data is None or len(data) == 0:

            return False

        return float(torch.tensor(data).float().pow(2).mean().sqrt()) > 0.02
