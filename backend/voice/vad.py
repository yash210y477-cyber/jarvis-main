import torch
import torchaudio
from silero_vad import load_silero_vad, get_speech_timestamps


class VoiceActivityDetector:

    def __init__(self):

        self.model = load_silero_vad()

        self.sample_rate = 16000

    def has_speech(self, audio):

        try:

            if audio is None:
                return False

            if isinstance(audio, torch.Tensor):
                waveform = audio
            else:
                waveform = torch.tensor(audio)

            waveform = waveform.float()

            if waveform.ndim > 1:
                waveform = waveform.mean(dim=1)

            if waveform.numel() == 0:
                return False

            timestamps = get_speech_timestamps(
                waveform,
                self.model,
                sampling_rate=self.sample_rate,
                threshold=0.5,
                min_speech_duration_ms=250,
                min_silence_duration_ms=300
            )

            return len(timestamps) > 0

        except Exception as e:

            print("VAD Error:", e)

            return False