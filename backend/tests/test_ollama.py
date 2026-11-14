"""The local Ollama provider: last-resort AI when the cloud keys fail."""

import json
from types import SimpleNamespace

import pytest

from providers import ollama as ollama_module
from providers.ollama import OllamaProvider


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def fake_models(monkeypatch, models):
    monkeypatch.setattr(
        ollama_module.urllib.request,
        "urlopen",
        lambda url, timeout=0: FakeResponse(
            {"models": [{"name": name} for name in models]}
        ),
    )


def test_picks_configured_model_when_installed(monkeypatch):

    monkeypatch.setattr(ollama_module.settings, "OLLAMA_MODEL", "qwen2.5:3b")
    fake_models(monkeypatch, ["qwen2.5:3b", "llama3.2:1b"])

    provider = OllamaProvider()

    assert provider.health() is True
    assert provider.model == "qwen2.5:3b"


def test_falls_back_to_an_installed_model(monkeypatch):

    monkeypatch.setattr(ollama_module.settings, "OLLAMA_MODEL", "not-installed")
    fake_models(monkeypatch, ["llama3.2:1b", "qwen2.5:3b"])

    provider = OllamaProvider()

    assert provider.model == "qwen2.5:3b"


def test_missing_model_is_not_healthy(monkeypatch):

    fake_models(monkeypatch, [])

    provider = OllamaProvider()

    assert provider.health() is False

    result = provider.chat("hello")

    assert result["success"] is False
    assert "not running" in result["error"]


def test_chat_returns_local_answer(monkeypatch):

    monkeypatch.setattr(ollama_module.settings, "OLLAMA_MODEL", "qwen2.5:3b")
    fake_models(monkeypatch, ["qwen2.5:3b"])

    provider = OllamaProvider()

    captured = {}

    def create(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="Local answer.", tool_calls=None)
                )
            ]
        )

    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    result = provider.chat("who are you")

    assert result == {
        "success": True,
        "provider": "ollama",
        "model": "qwen2.5:3b",
        "response": "Local answer.",
    }
    assert captured["model"] == "qwen2.5:3b"
    assert captured["messages"][0]["role"] == "system"
    assert "Hinglish" in captured["messages"][0]["content"]
    assert captured["messages"][1] == {"role": "user", "content": "who are you"}


def test_chat_error_is_reported(monkeypatch):

    monkeypatch.setattr(ollama_module.settings, "OLLAMA_MODEL", "qwen2.5:3b")
    fake_models(monkeypatch, ["qwen2.5:3b"])

    provider = OllamaProvider()

    def create(**kwargs):
        raise RuntimeError("connection reset")

    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    result = provider.chat("hello")

    assert result["success"] is False
    assert "connection reset" in result["error"]


def test_ollama_is_the_last_provider_and_answers(monkeypatch):
    """Cloud providers disabled -> the manager still answers from Ollama."""

    from providers.manager import AIManager

    for flag in (
        "ENABLE_OPENROUTER", "ENABLE_GROQ",
        "ENABLE_CEREBRAS", "ENABLE_DEEPSEEK", "ENABLE_ZAI",
        "ENABLE_SILICONFLOW",
    ):
        monkeypatch.setattr(ollama_module.settings, flag, False, raising=False)

    monkeypatch.setattr(ollama_module.settings, "ENABLE_OLLAMA", True)
    monkeypatch.setattr(ollama_module.settings, "OLLAMA_MODEL", "qwen2.5:3b")

    fake_models(monkeypatch, ["qwen2.5:3b"])

    manager = AIManager()

    assert [provider.name() for provider in manager.providers] == ["ollama"]

    def create(**kwargs):
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="Offline answer.", tool_calls=None
                    )
                )
            ]
        )

    manager.providers[0].client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    result = manager.chat("hello")

    assert result["success"] is True
    assert result["provider"] == "ollama"
    assert result["response"] == "Offline answer."


def test_priority_lists_ollama_last():

    from config.settings import settings

    assert settings.PROVIDER_PRIORITY[-1] == "ollama"
