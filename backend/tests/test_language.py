"""The reply language is the user's choice, not a guess from each message."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brain import language


@pytest.fixture(autouse=True)
def store(tmp_path, monkeypatch):
    from config.settings import settings

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "JARVIS_LANGUAGE", "auto")


def test_english_mode_answers_in_english_even_for_hinglish():
    language.set_language("english")

    assert language.reply_language("bhai kya haal hai") == "english"


def test_hinglish_mode_answers_in_hinglish_even_for_english():
    language.set_language("hinglish")

    assert language.reply_language("what is the weather today") == "hinglish"


def test_auto_follows_what_the_user_wrote():
    language.set_language("auto")

    assert language.reply_language("what is the weather today") == "english"
    assert language.reply_language("aaj mausam kaisa hai") == "hinglish"


def test_the_choice_survives_a_restart_and_rejects_nonsense():
    language.set_language("english")

    assert language.current() == "english"

    with pytest.raises(ValueError):
        language.set_language("french")


def test_settings_offers_three_choices():
    assert [item["id"] for item in language.options()] == ["auto", "english", "hinglish"]
