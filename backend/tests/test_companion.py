"""Push-to-talk companion, area ask, answer card, guided walkthrough."""

import json

from tools import card, companion, local_intents, orb, screen_agent, screen_area, screenshot


# --------------------------------------------------------------- screenshot


def test_capture_is_dpi_aware_and_full_desktop():
    assert "SetProcessDPIAware" in screenshot.SCRIPT
    assert "SetProcessDpiAwareness" in screenshot.SCRIPT
    assert "SystemInformation" in screenshot.SCRIPT
    assert "VirtualScreen" in screenshot.SCRIPT


# -------------------------------------------------------------------- card


def test_card_needs_some_text():
    assert card.show_card("JARVIS", "   ")["success"] is False


def test_card_writes_payload_and_opens_a_window(monkeypatch):
    opened = {}

    def fake_popen(args, **kwargs):
        opened["args"] = args
        return object()

    monkeypatch.setattr(card.subprocess, "Popen", fake_popen)

    result = card.show_card("Notes", "three short points", seconds=10)

    assert result["success"] is True
    assert opened["args"][0].endswith("python.exe") or "python" in opened["args"][0]

    payload_path = opened["args"][2].split("r\"")[1].split("\"")[0]

    with open(payload_path, encoding="utf-8") as handle:
        payload = json.load(handle)

    assert payload["body"] == "three short points"
    assert payload["seconds"] == 10


# --------------------------------------------------------------- area ask


def test_crop_cuts_the_selected_box(tmp_path, monkeypatch):
    from PIL import Image

    image = Image.new("RGB", (400, 300), "white")
    image.paste((255, 0, 0), (100, 50, 200, 150))

    source = tmp_path / "screen.png"
    image.save(source)

    area = screen_area.crop(str(source), {"x": 100, "y": 50, "w": 100, "h": 100})

    with Image.open(area) as piece:
        assert piece.size == (100, 100)
        assert piece.getpixel((10, 10)) == (255, 0, 0)


def test_crop_uses_the_desktop_origin(tmp_path):
    from PIL import Image

    image = Image.new("RGB", (400, 300), "black")
    source = tmp_path / "screen.png"
    image.save(source)

    area = screen_area.crop(
        str(source), {"x": -1400, "y": 120, "w": 60, "h": 40}, left=-1440, top=0
    )

    with Image.open(area) as piece:
        assert piece.size == (60, 40)


def test_area_without_a_selection_is_refused(monkeypatch):
    monkeypatch.setattr(
        screen_area, "select_region", lambda **kwargs: {"success": True, "rect": None}
    )

    result = screen_area.ask_area("yeh kya hai")

    assert result["success"] is False
    assert "area" in result["error"].lower()


# --------------------------------------------------------------- companion


class FakeSpeaker:
    def __init__(self):
        self.said = []

    def speak(self, text):
        self.said.append(text)


def test_configure_attaches_brain_and_voice():
    handler = lambda text: {"response": "ok"}

    result = companion.configure(handler=handler, speaker=FakeSpeaker())

    assert result["handler"] is True
    assert result["speaker"] is True


def test_a_phrase_is_answered_and_spoken(monkeypatch):
    said = FakeSpeaker()
    states = []

    monkeypatch.setattr(companion.orb, "set_state", lambda state, text="": states.append(state))

    companion.configure(handler=lambda text: {"response": f"heard {text}"}, speaker=said)
    companion.events()

    companion._respond("hello")

    assert said.said == ["heard hello"]
    assert states[0] == "thinking"
    assert states[-1] == "idle"


def test_status_reports_the_shortcuts():
    status = companion.status()

    assert status["shortcuts"]["talk"] == "hold Ctrl+Alt"
    assert status["shortcuts"]["area"] == "Ctrl+Shift+A"


def test_orb_state_round_trip(monkeypatch, tmp_path):
    monkeypatch.setattr(orb, "DATA", tmp_path)
    monkeypatch.setattr(orb, "STATE_FILE", tmp_path / "state.json")

    orb.set_state("listening", "listening")

    assert orb.get_state()["state"] == "listening"


# ----------------------------------------------------------------- intents


def test_area_phrases_use_the_area_tool():
    intent = local_intents.detect("yeh area samjhao")

    assert intent["tool"] == "ask_area"


def test_show_me_how_is_guided():
    intent = local_intents.detect("dikhao kaise export karte hain")

    assert intent["tool"] == "screen_task"
    assert intent["arguments"]["guided"] is True


def test_a_plain_click_stays_a_normal_screen_task():
    intent = local_intents.detect("is page pe search button dabao")

    assert intent["tool"] == "screen_task"
    assert "guided" not in intent["arguments"]


# ------------------------------------------------------- guided walkthrough


def test_guided_task_points_and_waits_instead_of_clicking(monkeypatch):
    plan = json.dumps(
        {"thought": "Format menu", "action": "click", "x": 120, "y": 240}
    )

    monkeypatch.setattr(
        screen_agent.screen_reader.vision,
        "see",
        lambda prompt, image: {"success": True, "answer": plan, "model": "fake"},
    )
    monkeypatch.setattr(
        screen_agent.screen_reader.screenshot,
        "capture_screen",
        lambda label="": {
            "success": True,
            "path": "fake.png",
            "left": -100,
            "top": 20,
        },
    )
    monkeypatch.setattr(screen_agent.screen_reader, "shrink", lambda path: path)

    rings = []
    monkeypatch.setattr(
        screen_agent, "show_arrow", lambda x, y, label="", ms=0: rings.append((x, y))
    )
    monkeypatch.setattr(
        screen_agent, "wait_for_click", lambda x, y, **kwargs: {"clicked": True, "x": x, "y": y}
    )

    def fail_click(x, y):
        raise AssertionError("guided mode must not click for the user")

    monkeypatch.setattr(screen_agent, "click", fail_click)

    result = screen_agent.run_task("export karna dikhao", guided=True)

    # The ring follows the screenshot origin, and the user did the clicking.
    assert rings and rings[0] == (20, 260)
    assert result["guided"] is True
    assert result["steps"][0]["detail"]["clicked"] is True
