"""Calls transcribe on Groq's Whisper, and use the local model when it fails."""

import numpy as np

from config.settings import settings


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_groq_transcribes_and_cleans_the_text(monkeypatch):
    from voice import stt

    seen = {}

    def fake_post(url, headers=None, files=None, data=None, timeout=None):
        seen["url"] = url
        seen["model"] = data["model"]
        seen["file"] = files["file"][0]
        seen["auth"] = headers["Authorization"]
        return FakeResponse({"text": " Jervis, Open Spotify please. "})

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(stt.requests, "post", fake_post)

    engine = stt.GroqSpeechToText()

    text = engine.transcribe(np.zeros(16000, dtype=np.float32))

    assert text == "jarvis, open spotify please."
    assert seen["url"].endswith("/audio/transcriptions")
    assert seen["model"] == settings.GROQ_STT_MODEL
    assert seen["file"] == "call.wav"
    assert seen["auth"] == "Bearer test-key"
    assert engine.last_error == ""


def test_a_failed_request_falls_back_to_the_local_model(monkeypatch):
    from voice import stt

    class Local:
        def transcribe(self, audio, language=None):
            return "local answer"

    def broken(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setattr(stt.requests, "post", broken)
    monkeypatch.setattr(stt, "shared", lambda: Local())

    engine = stt.GroqSpeechToText()

    assert engine.transcribe(np.zeros(16000, dtype=np.float32)) == "local answer"
    assert "network down" in engine.last_error


def test_calls_use_the_local_model_when_groq_is_off(monkeypatch):
    from voice import stt

    class Local:
        def transcribe(self, audio, language=None):
            return "local"

    monkeypatch.setattr(stt, "shared", lambda: Local())
    monkeypatch.setattr(stt, "_CALLS", None)
    monkeypatch.setattr(settings, "GROQ_STT", False)

    assert stt.network_stt() is False
    assert stt.calls().transcribe(np.zeros(16000, dtype=np.float32)) == "local"


def test_calls_use_groq_when_a_key_is_configured(monkeypatch):
    from voice import stt

    monkeypatch.setattr(stt, "_CALLS", None)
    monkeypatch.setattr(settings, "GROQ_STT", True)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    assert stt.network_stt() is True
    assert isinstance(stt.calls(), stt.GroqSpeechToText)
