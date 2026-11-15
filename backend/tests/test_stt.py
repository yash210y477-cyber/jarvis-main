"""The speech path must hear Hindi and Hinglish, not force everything to English."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice import speech, stt


def test_english_only_model_names_are_upgraded_to_multilingual(monkeypatch):
    monkeypatch.setattr(stt.settings, "STT_MODEL", "base.en")
    assert stt.model_name() == "base"

    monkeypatch.setattr(stt.settings, "STT_MODEL", "small")
    assert stt.model_name() == "small"


def test_auto_language_leaves_the_choice_to_whisper(monkeypatch):
    monkeypatch.setattr(stt.settings, "STT_LANGUAGE", "auto")
    assert stt.resolve_language(None) is None
    assert stt.resolve_language("auto") is None

    assert stt.resolve_language("hi") == "hi"
    assert stt.resolve_language("en") == "en"


def test_a_decoder_loop_is_not_treated_as_speech():
    assert stt.looks_broken("ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ ॐ")
    assert stt.looks_broken("adadadadadadadadadadadadadadad")
    assert stt.looks_broken("")

    assert not stt.looks_broken("screen band karo aur time kya hai")
    assert not stt.looks_broken("कल सुबह सात बजे मुझे उठा देना")


def test_hindi_transcript_becomes_the_hinglish_people_type():
    assert speech.to_hinglish("स्क्रीन बंद करो") == "skrin band karo"
    assert speech.to_hinglish("समय क्या है") == "samay kya hai"
    assert speech.to_hinglish("आज मौसम कैसा है") == "aaj mausam kaisa hai"
