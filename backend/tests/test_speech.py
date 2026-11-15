import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice import speech


def test_hinglish_is_spoken_by_a_hindi_voice():
    plan = speech.plan(
        "Aaj mausam bahut accha hai, aap kaise hain?",
        "en-IN-PrabhatNeural",
        speech.HINDI_MALE,
        speech.HINDI_FEMALE,
    )

    voice_name, text = plan[0]

    assert voice_name == "hi-IN-MadhurNeural"
    assert "आज" in text
    assert "?" not in text


def test_written_hindi_keeps_the_speaker_gender():
    text = "नमस्ते यश, आज कैसे हैं?"

    male = speech.plan(text, "en-GB-RyanNeural", speech.HINDI_MALE, speech.HINDI_FEMALE)
    female = speech.plan(text, "en-US-AriaNeural", speech.HINDI_MALE, speech.HINDI_FEMALE)

    assert male[0][0] == "hi-IN-MadhurNeural"
    assert female[0][0] == "hi-IN-SwaraNeural"


def test_english_stays_with_the_chosen_voice_and_loses_the_signs():
    plan = speech.plan(
        "Your meeting is at 5 pm. **Done** ✅ https://x.com/a",
        "en-GB-RyanNeural",
        speech.HINDI_MALE,
        speech.HINDI_FEMALE,
    )

    voice_name, text = plan[0]

    assert voice_name == "en-GB-RyanNeural"
    assert text == "Your meeting is at 5 pm. Done"


def test_markdown_and_symbols_never_reach_the_voice():
    assert speech.clean("`code` **bold** ~~gone~~ #tag ?") == "code bold gone tag"


def test_common_words_transliterate_whole():
    assert speech.to_devanagari("aaj kya karna hai") == "आज क्या करना है"
