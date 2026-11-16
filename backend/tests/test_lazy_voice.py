"""The voice stack must not load torch, pygame or whisper until it is used.

Importing the assistant used to pull in every heavy library at startup: torch for
the voice detector, pygame for the speaker and faster-whisper for speech. That
cost seconds of CPU on every start and on every reload. These tests pin the
lazy behaviour and prove the first real use still works.
"""

import subprocess
import sys
import types
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _run(code: str) -> str:
    finished = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(BACKEND),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert finished.returncode == 0, finished.stderr
    return finished.stdout.strip()


def test_importing_voice_does_not_load_heavy_libraries():
    loaded = _run(
        "import sys; "
        "import voice.engine, voice.tts, voice.stt, voice.vad, voice.recorder; "
        "print(sorted(m for m in ('torch', 'pygame', 'faster_whisper') if m in sys.modules))"
    )
    assert loaded == "[]"


def test_engine_starts_without_building_the_voice_pieces():
    built = _run(
        "import sys; import voice.engine; "
        "engine = voice.engine.VoiceEngine(); "
        "print(engine._recorder is None and engine._stt is None and engine._tts is None)"
    )
    assert built == "True"


def test_speaker_imports_pygame_on_first_use():
    loaded = _run(
        "import sys; import voice.tts; "
        "module = voice.tts._pygame(); "
        "print('pygame' in sys.modules and module.__name__ == 'pygame')"
    )
    assert loaded == "True"


def test_first_spoken_sentence_still_gets_a_working_pygame(monkeypatch):
    fake = types.SimpleNamespace(name="fake-pygame")

    monkeypatch.setitem(sys.modules, "pygame", fake)
    monkeypatch.setattr("voice.tts.pygame", None, raising=False)

    from voice import tts

    assert tts._pygame() is fake


def test_torch_is_opened_by_the_detector_on_first_use(monkeypatch):
    fake = types.SimpleNamespace(Tensor=object)

    monkeypatch.setitem(sys.modules, "torch", fake)

    from voice import vad

    assert vad._torch() is fake


def test_recorder_opens_torch_only_while_recording(monkeypatch):
    fake = types.SimpleNamespace()

    monkeypatch.setitem(sys.modules, "torch", fake)

    from voice import recorder

    assert recorder._torch() is fake


def test_transcriber_loads_whisper_when_it_is_first_needed(monkeypatch):
    """Building the transcriber is what pulls in faster-whisper, not importing it."""

    calls = []

    class FakeWhisperModel:
        def __init__(self, **settings):
            calls.append(settings)

    fake = types.ModuleType("faster_whisper")
    fake.WhisperModel = FakeWhisperModel

    monkeypatch.setitem(sys.modules, "faster_whisper", fake)

    from voice.stt import SpeechToText

    transcriber = SpeechToText()

    assert calls, "the whisper model is built on first use"
    assert calls[0]["model_size_or_path"] == transcriber.name
