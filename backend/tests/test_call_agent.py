"""Phase B: the Telegram call conversation pipeline, tested without Telegram."""

import asyncio
import wave

import numpy as np
import pytest

from remote import call_agent


class FakeCalls:
    def __init__(self):
        self.played = []
        self.recorded = []

    async def play(self, chat_id, stream):
        self.played.append(chat_id)

    async def record(self, chat_id, stream):
        self.recorded.append(chat_id)


class FakeBrain:
    def __init__(self, reply="Opening calculator."):
        self.messages = []
        self.reply = reply

    def chat(self, message):
        self.messages.append(message)
        return {"success": True, "action": "open_app", "response": self.reply}


def _call_chunk(amplitude=8000, seconds=call_agent.CHUNK_SECONDS):
    """One 250 ms chunk of call-format audio, as Telegram would deliver it."""

    rate = call_agent.SAMPLE_RATE

    samples = int(rate * seconds)

    tone = (
        amplitude
        * np.sin(2 * np.pi * 300 * np.arange(samples) / rate)
    ).astype(np.int16)

    stereo = np.repeat(tone, 2).astype(np.int16)

    return stereo.tobytes()


SILENCE = b"\x00" * len(_call_chunk())


def test_pcm_to_float_downmixes_stereo():

    payload = np.array([1000, 3000, -1000, -3000], dtype=np.int16).tobytes()

    mono = call_agent.pcm_to_float(payload)

    assert mono.shape == (2,)
    assert mono[0] == pytest.approx(2000 / 32768)
    assert mono[1] == pytest.approx(-2000 / 32768)


def test_pcm_to_float_survives_odd_buffer():

    payload = np.array([1000, 2000, 500], dtype=np.int16).tobytes()

    mono = call_agent.pcm_to_float(payload)

    assert mono.size == 1


def test_resample_48k_to_16k_length():

    samples = np.zeros(call_agent.SAMPLE_RATE, dtype=np.float32)

    out = call_agent.resample(samples)

    assert out.size == call_agent.TARGET_RATE


def test_clean_for_speech_drops_markup():

    text = call_agent.clean_for_speech(
        "**Done.**\n- opened calculator\n- https://example.com/docs"
    )

    assert "*" not in text
    assert "https://" not in text
    assert "opened calculator" in text


def test_speak_clip_writes_playable_wav():

    path = call_agent.speak_clip("Reminder, drink water.")

    assert path is not None and path.exists()

    assert path.stat().st_size > 1000

    assert call_agent.clip_duration(path) > 0.4

    path.unlink()


def test_feed_closes_utterance_after_silence():

    conversation = call_agent.CallConversation(calls=FakeCalls(), chat_id=5)

    conversation._vad = False  # use the volume gate, no silero model needed

    finished = []

    for _ in range(4):
        finished += conversation.feed(_call_chunk())

    assert finished == []

    for _ in range(5):
        finished += conversation.feed(SILENCE)

    assert len(finished) == 1

    seconds = len(finished[0]) / (
        call_agent.SAMPLE_RATE * call_agent.SAMPLE_WIDTH * call_agent.CHANNELS
    )

    assert seconds > 1.0

    assert conversation._utterance == b""


def test_silence_only_is_not_a_request():

    conversation = call_agent.CallConversation(calls=FakeCalls(), chat_id=5)

    conversation._vad = False

    finished = []

    for _ in range(8):
        finished += conversation.feed(SILENCE)

    assert finished == []


def test_call_turn_thinks_and_speaks(monkeypatch):

    calls = FakeCalls()
    brain = FakeBrain()

    conversation = call_agent.CallConversation(calls, brain=brain, chat_id=77)

    monkeypatch.setattr(
        conversation, "_transcribe", lambda payload: "open calculator"
    )

    result = asyncio.run(conversation.handle(b"\x00" * 4800))

    assert result["success"] is True
    assert result["heard"] == "open calculator"

    # The tool brain got the request with the wake word.
    assert brain.messages == ["jarvis open calculator"]

    assert conversation.turns == 1
    assert conversation.last_reply == "Opening calculator."

    # Reply played into the call, then listening resumed.
    assert calls.played == [77]
    assert calls.recorded == [77]
    assert conversation.listening is True
    assert conversation.speaking is False


def test_unheard_audio_does_not_reply(monkeypatch):

    calls = FakeCalls()

    conversation = call_agent.CallConversation(calls, brain=FakeBrain(), chat_id=9)

    monkeypatch.setattr(conversation, "_transcribe", lambda payload: "")

    result = asyncio.run(conversation.handle(b"\x00" * 4800))

    assert result["success"] is False
    assert calls.played == []
    assert conversation.turns == 0


def test_whisper_understands_generated_speech(tmp_path):

    """Real STT check: SAPI speech -> whisper, the exact call pipeline."""

    from voice.stt import SpeechToText

    clip = call_agent.speak_clip("Open calculator")

    assert clip is not None

    with wave.open(str(clip), "rb") as handle:

        rate = handle.getframerate()

        frames = handle.readframes(handle.getnframes())

    samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

    speech = call_agent.resample(samples, rate, call_agent.TARGET_RATE)

    text = SpeechToText().transcribe(speech, language="en")

    clip.unlink()

    assert "calculator" in text.lower()
