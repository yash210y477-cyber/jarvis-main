"""Small talk must not be mistaken for a volume or playback command."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import local_intents, nlu

HARMLESS = [
    "thoda zyada bata do iske bare me",
    "bhai wo jo kal wala kaam tha na usko thoda aage badha do",
    "stop thinking about it and just tell me",
    "next week ka weather kaisa hai",
    "mera volume kitna hai ye mat batao, mood kharab hai",
]


def test_unrelated_sentences_are_left_to_the_model():
    for message in HARMLESS:

        assert nlu.interpret(message) is None, message
        assert local_intents.detect(message) is None, message


def test_real_volume_requests_still_work():
    assert nlu.interpret("volume kam karo")["arguments"]["action"] == "volume_down"
    assert nlu.interpret("awaaz tez karo")["arguments"]["action"] == "volume_up"
    assert nlu.interpret("sound up karo")["arguments"]["action"] == "volume_up"


def test_playback_words_need_a_media_sentence():
    assert nlu.interpret("pause music")["arguments"]["action"] == "play_pause"
    assert nlu.interpret("next song")["arguments"]["action"] == "next"

    # Alone they are the whole request, so they still work.
    assert nlu.interpret("ruk jao")["arguments"]["action"] == "play_pause"
    assert nlu.interpret("skip")["arguments"]["action"] == "next"
