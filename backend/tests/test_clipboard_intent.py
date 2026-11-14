from tools import local_intents


def test_copy_strips_the_destination_words():
    for message in (
        "copy hello jarvis to clipboard",
        "copy hello jarvis into the clipboard",
        "clipboard pe hello jarvis copy karo",
    ):
        intent = local_intents.detect(message)

        assert intent["tool"] == "set_clipboard"
        assert "clipboard" not in intent["arguments"]["text"].lower()
        assert "hello jarvis" in intent["arguments"]["text"].lower()


def test_copy_keeps_a_simple_phrase_whole():
    intent = local_intents.detect("copy invoice number 42")

    assert intent["arguments"]["text"] == "invoice number 42"


def test_reading_the_clipboard_still_works():
    assert local_intents.detect("what is in my clipboard")["tool"] == "get_clipboard"
