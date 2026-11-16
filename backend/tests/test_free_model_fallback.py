"""A failed free model hands the prompt to the next free model of its provider."""

from types import SimpleNamespace

from providers.groq import GroqProvider
from providers.openrouter import OpenRouterProvider
from config.settings import settings


class Reply:
    def __init__(self, status, payload):

        self.status_code = status
        self._payload = payload

    def json(self):

        return self._payload


def groq_provider(available):
    provider = GroqProvider.__new__(GroqProvider)

    provider.provider_name = "groq"
    provider.model = "openai/gpt-oss-120b"
    provider.fallback_model = "qwen/qwen3.8-27b"
    provider._known = set(available)

    asked = []

    def create(**kwargs):

        asked.append(kwargs["model"])

        if kwargs["model"] == "openai/gpt-oss-120b":

            raise RuntimeError("429 rate_limit_exceeded")

        return SimpleNamespace(
            model=kwargs["model"],
            choices=[
                SimpleNamespace(message=SimpleNamespace(content="Second model answered."))
            ],
        )

    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    return provider, asked


def test_groq_asks_the_next_free_model_when_the_first_fails(monkeypatch):

    monkeypatch.setattr("providers.groq.ranking.models", lambda role="text": [])

    provider, asked = groq_provider({"openai/gpt-oss-120b", "qwen/qwen3.8-27b"})

    result = provider.chat("hello")

    assert result["success"] is True
    assert result["model"] == "qwen/qwen3.8-27b"
    assert result["response"] == "Second model answered."
    assert asked == ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"]


def test_groq_stops_on_a_bad_key(monkeypatch):

    monkeypatch.setattr("providers.groq.ranking.models", lambda role="text": [])

    provider, _asked = groq_provider({"openai/gpt-oss-120b", "qwen/qwen3.8-27b"})

    def create(**kwargs):

        raise RuntimeError("401 invalid api key")

    provider.client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    result = provider.chat("hello")

    assert result["success"] is False
    assert "401" in result["error"]


def test_openrouter_asks_the_next_free_model_when_the_first_fails(monkeypatch):

    monkeypatch.setattr("providers.openrouter.ranking.models", lambda role="text": [])

    provider = OpenRouterProvider()
    provider.api_key = "test-key"

    asked = []

    def post(url, headers=None, json=None, timeout=None):

        asked.append(json["model"])

        if len(asked) == 1:

            return Reply(429, {"error": {"message": "free-models-per-day"}})

        return Reply(200, {"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr("providers.openrouter.requests.post", post)

    result = provider.chat("hello")

    assert result["success"] is True
    assert result["model"] == settings.OPENROUTER_FREE_MODELS[1]
    assert asked == list(settings.OPENROUTER_FREE_MODELS[:2])
