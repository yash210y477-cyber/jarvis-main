import base64
from pathlib import Path

import pytest

from tools import image_gen


class FakeResponse:
    status_code = 200
    headers = {"content-type": "application/json"}
    text = ""

    def __init__(self, payload, status_code=200, text=""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


class FakePicture:
    """An image reply from the keyless fallback service."""

    status_code = 200
    headers = {"content-type": "image/jpeg"}

    def __init__(self, content):
        self.content = content


QUOTA_TEXT = (
    '{"error":{"message":"Rate limit exceeded: free-models-per-day","code":429,'
    '"metadata":{"headers":{"X-RateLimit-Limit":"50","X-RateLimit-Remaining":"0",'
    '"X-RateLimit-Reset":"1794873600000"}}}}'
)


@pytest.fixture
def png_b64():
    return base64.b64encode(b"\x89PNG\r\n\x1a\nfake-bytes").decode()


def test_pictures_never_land_in_the_data_folder():
    """Only the Download button may leave a picture on the machine."""

    from memory.storage import data_dir

    folder = image_gen.images_dir()

    assert folder != data_dir() / "images"
    assert data_dir() not in folder.parents


def test_the_cache_drops_pictures_nobody_downloaded(tmp_path, monkeypatch):
    monkeypatch.setattr(image_gen, "images_dir", lambda: tmp_path)

    old = tmp_path / "old.png"
    old.write_bytes(b"x")
    fresh = tmp_path / "fresh.png"
    fresh.write_bytes(b"y")

    stale = 1700000000

    import os

    os.utime(old, (stale, stale))

    image_gen.prune(hours=1)

    assert not old.exists()
    assert fresh.exists()


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


def test_a_spent_free_quota_still_draws_through_the_keyless_service(tmp_path, monkeypatch):
    """The 50-a-day free limit must not make the drawing tool fail for the day."""

    import io

    from PIL import Image

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("IMAGE_FALLBACK", raising=False)
    monkeypatch.setattr(image_gen, "images_dir", lambda: tmp_path)

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="JPEG")

    asked = {}

    def fake_post(url, headers=None, data=None, timeout=None):
        return FakeResponse({}, status_code=429, text=QUOTA_TEXT)

    def fake_get(url, timeout=None):
        asked["url"] = url
        return FakePicture(buffer.getvalue())

    monkeypatch.setattr(image_gen.requests, "post", fake_post)
    monkeypatch.setattr(image_gen.requests, "get", fake_get)

    result = image_gen.generate_image("a red square")

    assert result["success"] is True
    assert result["provider"].startswith("pollinations/")
    assert "fallback" in result["message"]
    assert "flux" in asked["url"]

    saved = tmp_path / Path(result["paths"][0]).name

    with Image.open(saved) as picture:
        assert picture.format == "PNG"


def test_the_quota_error_names_the_reset_time(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("IMAGE_FALLBACK", "0")
    monkeypatch.setattr(image_gen, "images_dir", lambda: tmp_path)

    def fake_post(url, headers=None, data=None, timeout=None):
        return FakeResponse({}, status_code=429, text=QUOTA_TEXT)

    monkeypatch.setattr(image_gen.requests, "post", fake_post)

    result = image_gen.generate_image("a red square")

    assert result["success"] is False
    assert "quota returns at" in result["error"]


def test_the_fallback_can_be_switched_off(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("IMAGE_FALLBACK", "0")
    monkeypatch.setattr(image_gen, "images_dir", lambda: tmp_path)

    def fake_post(url, headers=None, data=None, timeout=None):
        return FakeResponse({}, status_code=429, text=QUOTA_TEXT)

    called = {"get": False}

    def fake_get(url, timeout=None):
        called["get"] = True
        return FakePicture(b"")

    monkeypatch.setattr(image_gen.requests, "post", fake_post)
    monkeypatch.setattr(image_gen.requests, "get", fake_get)

    result = image_gen.generate_image("a red square")

    assert result["success"] is False
    assert called["get"] is False
