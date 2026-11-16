import base64
from pathlib import Path

import pytest

from providers.zai import ZaiProvider
from tools import local_intents, screen_reader


def test_page_questions_route_to_screen_reading():
    for message in (
        "summarize this page",
        "yeh page kya hai samjhao",
        "read my screen",
        "screen dekho kya likha hai",
    ):
        intent = local_intents.detect(message)

        assert intent["tool"] == "read_screen"
        assert intent["arguments"]["question"] == message


def test_a_plain_screenshot_stays_a_screenshot():
    assert local_intents.detect("take a screenshot")["tool"] == "screenshot"


def test_vision_answer_is_rendered(tmp_path):
    result = {"success": True, "result": {"answer": "A GitHub page about Python."}}

    assert "GitHub" in local_intents.render("read_screen", result)


def test_shrink_makes_a_smaller_jpeg(tmp_path):
    from PIL import Image

    source = tmp_path / "shot.png"

    Image.new("RGB", (3000, 1200), "white").save(source)

    small = screen_reader.shrink(str(source))

    assert small.exists()
    assert small.suffix == ".jpg"

    with Image.open(small) as image:
        assert image.width == screen_reader.MAX_WIDTH


def test_read_screen_returns_the_answer(monkeypatch, tmp_path):
    shot = tmp_path / "shot.png"

    from PIL import Image

    Image.new("RGB", (60, 40), "white").save(shot)

    monkeypatch.setattr(
        screen_reader.screenshot,
        "capture_screen",
        lambda label="": {"success": True, "path": str(shot)},
    )

    seen = {}

    def fake_see(question, image_path):
        seen["question"] = question
        seen["image"] = image_path
        return {"success": True, "model": "glm-4.6v-flash", "answer": "A browser page."}

    monkeypatch.setattr(screen_reader.vision, "see", fake_see)

    result = screen_reader.read_screen("yeh page kya hai")

    assert result["success"] is True
    assert result["answer"] == "A browser page."
    assert seen["question"] == "yeh page kya hai"
    assert Path(seen["image"]).exists()


def test_capture_failure_is_reported(monkeypatch):
    monkeypatch.setattr(
        screen_reader.screenshot,
        "capture_screen",
        lambda label="": {"success": False, "error": "no display"},
    )

    result = screen_reader.read_screen("read my screen")

    assert result["success"] is False
    assert "no display" in result["error"]


class FakeMessage:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


class FakeClient:
    def __init__(self, working_model):
        self.working_model = working_model
        self.payloads = []

        class Completions:
            def __init__(self, outer):
                self.outer = outer

            def create(self, **kwargs):
                self.outer.payloads.append(kwargs)

                if kwargs["model"] != self.outer.working_model:
                    raise RuntimeError("model not available")

                reply = type("Reply", (), {})()
                reply.choices = [
                    type("Choice", (), {"message": FakeMessage("Two windows open.")})()
                ]
                reply.model = kwargs["model"]

                return reply

        self.chat = type("Chat", (), {})()
        self.chat.completions = Completions(self)


@pytest.fixture(autouse=True)
def clean_wallet():
    from providers import zai

    zai.reset_state()

    yield

    zai.reset_state()


def build_vision_provider(tmp_path, working="glm-4.6v-flash"):
    image = tmp_path / "shot.jpg"
    image.write_bytes(b"fake-jpeg")

    provider = ZaiProvider.__new__(ZaiProvider)

    provider.provider_name = "zai"
    provider.api_key = "test-key"
    provider.model = "glm-4.7-flash"
    provider._working = None
    provider.client = FakeClient(working)

    return provider, str(image)


def test_see_sends_the_image_as_a_data_url(tmp_path):
    provider, image = build_vision_provider(tmp_path)

    result = provider.see("what is on my screen?", image)

    assert result["success"] is True
    assert result["answer"] == "Two windows open."

    payload = provider.client.payloads[0]
    content = payload["messages"][0]["content"]

    assert content[0]["text"] == "what is on my screen?"
    assert content[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")

    assert base64.b64decode(content[1]["image_url"]["url"].split(",", 1)[1]) == b"fake-jpeg"


def test_see_never_falls_back_to_a_paid_vision_model(tmp_path):
    provider, image = build_vision_provider(tmp_path, working="glm-4.6v")

    result = provider.see("summarize this page", image)

    assert result["success"] is False

    asked = [payload["model"] for payload in provider.client.payloads]

    assert asked == ["glm-4.6v-flash"], "a paid vision model was asked"


def test_see_asks_only_the_free_vision_model(tmp_path):
    provider, image = build_vision_provider(tmp_path)

    result = provider.see("what is on my screen?", image)

    assert result["success"] is True

    asked = [payload["model"] for payload in provider.client.payloads]

    assert asked == ["glm-4.6v-flash"]


def test_see_without_a_key_reports_it(monkeypatch, tmp_path):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)

    provider = ZaiProvider()

    assert provider.health() is False
    assert provider.see("hi", str(tmp_path / "x.png"))["success"] is False


def test_a_failed_vision_model_says_so_plainly(monkeypatch, tmp_path):
    shot = tmp_path / "shot.png"

    from PIL import Image

    Image.new("RGB", (40, 30), "white").save(shot)

    monkeypatch.setattr(
        screen_reader.screenshot,
        "capture_screen",
        lambda label="": {"success": True, "path": str(shot)},
    )

    monkeypatch.setattr(
        screen_reader.vision,
        "see",
        lambda question, image_path: {
            "success": False,
            "error": "Error code: 429 - {'error': {'code': '1113', 'message': 'Insufficient balance'}}",
        },
    )

    result = screen_reader.read_screen("summarize this page")

    assert result["success"] is False
    assert "no free vision model" in result["error"].lower()
