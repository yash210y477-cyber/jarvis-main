from pathlib import Path

from PIL import Image

from tools import local_intents, screen_watch


def test_watch_phrases_are_recognised():
    assert local_intents.detect("watch my screen")["tool"] == "screen_watch_start"
    assert local_intents.detect("screen dekhte raho")["tool"] == "screen_watch_start"
    assert local_intents.detect("stop watching my screen")["tool"] == "screen_watch_stop"
    assert local_intents.detect("screen watch status")["tool"] == "screen_watch_status"
    assert local_intents.detect("open spotify")["tool"] == "open_app"


def test_start_without_a_key_is_refused(monkeypatch):
    class NoKey:
        def health(self):
            return False

    monkeypatch.setattr("providers.zai.ZaiProvider", NoKey)

    watcher = screen_watch.ScreenWatcher()

    result = watcher.start()

    assert result["success"] is False
    assert "ZAI_API_KEY" in result["error"]
    assert watcher.status()["watching"] is False


class FakeProvider:
    def health(self):
        return True

    def see(self, question, image_path):
        return {"success": True, "answer": "This is a login page."}


def build(monkeypatch, tmp_path):
    watcher = screen_watch.ScreenWatcher(interval=1, cooldown=1)

    monkeypatch.setattr(watcher, "_save", lambda image, kind: tmp_path / f"{kind}.jpg")
    monkeypatch.setattr(watcher, "_ask", lambda question, path: "This is a login page.")
    monkeypatch.setattr(watcher, "_announce", lambda text: None)

    return watcher


def test_page_explanation_is_recorded(monkeypatch, tmp_path):
    watcher = build(monkeypatch, tmp_path)

    image = Image.new("RGB", (200, 100), "white")

    assert watcher._explain_page(image) is True

    events = watcher.since(0)

    assert len(events) == 1
    assert events[0]["kind"] == "page"
    assert "login page" in events[0]["text"]
    assert watcher.status()["last_kind"] == "page"


def test_cursor_point_is_cropped_and_explained(monkeypatch, tmp_path):
    watcher = build(monkeypatch, tmp_path)

    seen = {}

    def fake_save(image, kind):
        seen["size"] = image.size

        return tmp_path / f"{kind}.jpg"

    monkeypatch.setattr(watcher, "_save", fake_save)

    image = Image.new("RGB", (1200, 800), "white")

    assert watcher._explain_cursor(image, (600, 400)) is True

    assert seen["size"] == (watcher.crop * 2, watcher.crop * 2)

    assert watcher.since(0)[0]["kind"] == "cursor"


def test_empty_answer_is_not_an_event(monkeypatch, tmp_path):
    watcher = build(monkeypatch, tmp_path)

    monkeypatch.setattr(watcher, "_ask", lambda question, path: "")

    image = Image.new("RGB", (100, 60), "white")

    assert watcher._explain_page(image) is False
    assert watcher.since(0) == []


def test_events_can_be_read_from_an_offset(monkeypatch, tmp_path):
    watcher = build(monkeypatch, tmp_path)

    image = Image.new("RGB", (100, 60), "white")

    watcher._explain_page(image)
    watcher._explain_page(image)

    first = watcher.since(0)[0]

    assert len(watcher.since(0)) == 2
    assert len(watcher.since(first["id"])) == 1


def test_stop_reports_the_count(monkeypatch, tmp_path):
    watcher = build(monkeypatch, tmp_path)

    result = watcher.stop()

    assert result["watching"] is False
    assert "Stopped" in result["message"]


def test_a_dead_vision_model_stops_the_watcher(monkeypatch, tmp_path):
    watcher = build(monkeypatch, tmp_path)

    monkeypatch.setattr(
        watcher,
        "_ask",
        lambda question, path: (
            watcher.__setattr__("error", "429 insufficient balance") or ""
        ),
    )

    watcher.running = True

    image = Image.new("RGB", (100, 60), "white")

    # The ask helper is replaced, so drive the real one through a fake provider.
    from tools import screen_watch as module

    class NoMoney:
        def health(self):
            return True

        def see(self, question, image_path):
            return {"success": False, "error": "429 Insufficient balance"}

    monkeypatch.setattr("providers.zai.ZaiProvider", NoMoney)

    watcher._ask = module.ScreenWatcher._ask.__get__(watcher)

    assert watcher._ask("what is this", tmp_path / "x.jpg") == ""
    assert watcher.running is False
    assert "no free vision model" in watcher.error.lower()
