from tools import local_intents, typing


def test_write_something_here_is_dictation():
    assert local_intents.detect("write hello here") == {
        "tool": "type_here",
        "arguments": {"text": "hello"},
    }

    assert local_intents.detect("type jarvis is online here")["arguments"]["text"] == (
        "jarvis is online"
    )


def test_hinglish_dictation():
    intent = local_intents.detect("hello likho")

    assert intent["tool"] == "type_here"
    assert intent["arguments"]["text"] == "hello"

    assert local_intents.detect("yahan likho good morning")["arguments"]["text"] == (
        "good morning"
    )


def test_a_normal_question_is_not_dictation():
    assert local_intents.detect("write a python function to reverse a list") is None
    assert local_intents.detect("type this on the page")["tool"] == "screen_task"
    assert local_intents.detect("open spotify")["tool"] == "open_app"


class FakeClipboard:
    def __init__(self, content=""):
        self.content = content
        self.sets = []

    def get_clipboard(self):
        return {"success": True, "content": self.content}

    def set_clipboard(self, text):
        self.sets.append(text)
        self.content = text
        return {"success": True}


def test_type_here_pastes_and_restores_the_clipboard(monkeypatch):
    fake = FakeClipboard("old clipboard")

    monkeypatch.setattr(typing, "clipboard", fake)
    monkeypatch.setattr(typing, "_paste", lambda: None)
    monkeypatch.setattr(typing.time, "sleep", lambda *a, **k: None)

    result = typing.type_here("hello world")

    assert result["success"] is True
    assert result["text"] == "hello world"
    assert fake.sets == ["hello world", "old clipboard"]


def test_empty_text_is_refused(monkeypatch):
    monkeypatch.setattr(typing, "clipboard", FakeClipboard(""))

    result = typing.type_here("   ")

    assert result["success"] is False


def test_render_shows_the_message():
    result = {"success": True, "result": {"message": 'Typed "hello" where the cursor was.'}}

    assert "Typed" in local_intents.render("type_here", result)
