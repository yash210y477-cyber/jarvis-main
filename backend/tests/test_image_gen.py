import base64
from pathlib import Path

import pytest

from tools import image_gen


class FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


@pytest.fixture
def png_b64():
    return base64.b64encode(b"\x89PNG\r\n\x1a\nfake-bytes").decode()


def test_image_is_saved_from_the_openrouter_reply(tmp_path, monkeypatch, png_b64):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(image_gen, "images_dir", lambda: tmp_path)

    sent = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        sent.update({"url": url, "headers": headers, "data": data})
        return FakeResponse({"data": [{"b64_json": png_b64}]})

    monkeypatch.setattr(image_gen.requests, "post", fake_post)

    result = image_gen.generate_image("a cat on the moon")

    assert result["success"] is True
    assert result["prompt"] == "a cat on the moon"
    assert result["count"] == 1

    saved = tmp_path / result["paths"][0].split("\\")[-1].split("/")[-1]
    assert saved.exists() and saved.read_bytes().startswith(b"\x89PNG")

    assert sent["url"] == image_gen.URL
    assert sent["headers"]["Authorization"] == "Bearer test-key"
    assert '"recraft' in sent["data"]


def test_missing_key_is_reported_not_crashed(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    result = image_gen.generate_image("a cat")

    assert result["success"] is False
    assert "OPENROUTER_API_KEY" in result["error"]


def test_empty_prompt_is_refused(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    result = image_gen.generate_image("   ")

    assert result["success"] is False


def test_image_sentences_reach_the_tool():
    from tools import nlu

    assert nlu.interpret("generate an image of a cat on the moon") == {
        "tool": "generate_image",
        "arguments": {"prompt": "a cat on the moon"},
    }

    assert nlu.interpret("draw a dragon")["tool"] == "generate_image"

    # Searching the web for a picture is not drawing one.
    assert nlu.interpret("search image on google") is None


def test_model_picker_maps_to_a_provider():
    from providers.manager import AIManager

    manager = AIManager()

    assert manager.find("auto") is None
    assert manager.find("") is None
    assert manager.find("llama3 (local)").name() == "ollama"
    assert manager.find("openrouter").name() == "openrouter"
    assert manager.find("nonsense") is None


def test_a_webp_reply_is_stored_as_real_png(tmp_path, monkeypatch):
    import io

    from PIL import Image

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(image_gen, "images_dir", lambda: tmp_path)

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="WEBP")
    webp_b64 = base64.b64encode(buffer.getvalue()).decode()

    def fake_post(url, headers=None, data=None, timeout=None):
        return FakeResponse({"data": [{"b64_json": webp_b64}]})

    monkeypatch.setattr(image_gen.requests, "post", fake_post)

    result = image_gen.generate_image("a red square")

    assert result["success"] is True

    saved = tmp_path / Path(result["paths"][0]).name

    with Image.open(saved) as picture:
        assert picture.format == "PNG"
