import pytest

from providers.zai import ZaiProvider


class FakeMessage:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeReply:
    def __init__(self, content, model):
        self.choices = [FakeChoice(content)]
        self.model = model


class FakeClient:
    def __init__(self, working_model):
        self.working_model = working_model
        self.asked = []

        class Completions:
            def __init__(self, outer):
                self.outer = outer

            def create(self, **kwargs):
                model = kwargs["model"]
                self.outer.asked.append(model)

                if model != self.outer.working_model:
                    raise RuntimeError("model not available")

                return FakeReply("Hello from GLM", model)

        self.chat = type("Chat", (), {})()
        self.chat.completions = Completions(self)


def build(working_model="glm-4.6"):
    provider = ZaiProvider.__new__(ZaiProvider)

    provider.provider_name = "zai"
    provider.api_key = "test-key"
    provider.model = "glm-4.6"
    provider._working = None
    provider.client = FakeClient(working_model)

    return provider


def test_missing_key_is_reported(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)

    provider = ZaiProvider()

    assert provider.health() is False
    assert provider.chat("hi")["success"] is False


def test_first_model_answers():
    provider = build("glm-4.6")

    result = provider.chat("hi")

    assert result["success"] is True
    assert result["provider"] == "zai"
    assert result["response"] == "Hello from GLM"


def test_retired_model_falls_through_to_the_next():
    provider = build("glm-4.7")

    result = provider.chat("hi")

    assert result["success"] is True
    assert result["model"] == "glm-4.7"
    assert provider._working == "glm-4.7"


def test_no_model_answering_returns_the_error():
    provider = build("nothing")

    result = provider.chat("hi")

    assert result["success"] is False
    assert "model not available" in result["error"]
