"""A file the agent wrote must reach Telegram as a document, not as text."""

from remote import telegram
from tools import files as store


def test_file_markers_are_split_from_the_reply():
    body, paths = telegram.file_marks(
        "Here is your game.\n[file]ShootingGame.java"
    )

    assert body == "Here is your game."
    assert paths == ["ShootingGame.java"]

    body, paths = telegram.file_marks("Done.")

    assert body == "Done."
    assert paths == []

    _, paths = telegram.file_marks("[file]my%20game.java")

    assert paths == ["my game.java"]


def test_a_generated_file_is_uploaded(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "workspace_root", lambda: tmp_path)

    game = tmp_path / "Game.java"
    game.write_text("class Game {}", encoding="utf-8")

    sent = {}

    class Response:
        def json(self):
            return {"ok": True}

    def fake_post(url, data=None, files=None, timeout=None):
        sent["url"] = url
        sent["chat"] = data["chat_id"]
        sent["name"] = files["document"][0]
        return Response()

    monkeypatch.setattr(telegram.requests, "post", fake_post)

    bridge = telegram.TelegramBridge(token="test", chat_ids="")

    assert bridge._send_document(7, "Game.java") is True
    assert sent["chat"] == 7
    assert sent["name"] == "Game.java"
    assert sent["url"].endswith("/sendDocument")


def test_a_path_outside_the_workspace_is_never_uploaded(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "workspace_root", lambda: tmp_path)

    calls = []

    monkeypatch.setattr(
        telegram.requests, "post", lambda *args, **kwargs: calls.append(args)
    )

    bridge = telegram.TelegramBridge(token="test", chat_ids="")

    assert bridge._send_document(7, "../outside.txt") is False
    assert calls == []
