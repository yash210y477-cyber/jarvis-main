"""The spoken voice follows the reply language chosen in Settings."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brain import language
from voice import speech

MALE = "en-IN-PrabhatNeural"
FEMALE = "en-US-AriaNeural"


@pytest.fixture(autouse=True)
def mode(tmp_path, monkeypatch):
    """A fresh language choice per test: auto unless the test picks one."""

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))
    language.set_language("auto")


def plan(text, voice=MALE):
    return speech.plan(text, voice, speech.HINDI_MALE, speech.HINDI_FEMALE)


def test_auto_speaks_hinglish_with_the_hindi_voice():
    voice, text = plan("Aaj mausam bahut accha hai, aap kaise hain?")[0]

    assert voice == "hi-IN-MadhurNeural"
    assert "आज" in text
    assert "?" not in text


def test_english_mode_uses_the_chosen_voice_even_for_hinglish_text():
    language.set_language("english")

    voice, text = plan("Aaj mausam bahut accha hai")[0]

    assert voice == MALE
    assert text == "Aaj mausam bahut accha hai"


def test_hinglish_mode_uses_the_hindi_voice_even_for_english_text():
    language.set_language("hinglish")

    voice, _ = plan("Your meeting is at 5 pm")[0]

    assert voice == "hi-IN-MadhurNeural"


def test_hinglish_mode_keeps_the_speaker_gender():
    language.set_language("hinglish")

    assert plan("Ho gaya, file save kar di", FEMALE)[0][0] == "hi-IN-SwaraNeural"


def test_written_hindi_keeps_the_speaker_gender():
    text = "नमस्ते यश, आज कैसे हैं?"

    assert plan(text, "en-GB-RyanNeural")[0][0] == "hi-IN-MadhurNeural"
    assert plan(text, FEMALE)[0][0] == "hi-IN-SwaraNeural"


def test_english_stays_with_the_chosen_voice_and_loses_the_signs():
    voice, text = plan("Your meeting is at 5 pm. **Done** ✅ https://x.com/a", "en-GB-RyanNeural")[0]

    assert voice == "en-GB-RyanNeural"
    assert text == "Your meeting is at 5 pm. Done"


def test_markdown_and_symbols_never_reach_the_voice():
    assert speech.clean("`code` **bold** ~~gone~~ #tag ?") == "code bold gone tag"


def test_common_words_transliterate_whole():
    assert speech.to_devanagari("aaj kya karna hai") == "आज क्या करना है"
