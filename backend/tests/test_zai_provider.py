import pytest

from providers import zai
from providers.zai import ZaiProvider


@pytest.fixture(autouse=True)
def empty_wallet_forgotten():
    """A balance cooldown must never leak from one test to the next."""

    zai.reset_balance_cooldown()

    yield

    zai.reset_balance_cooldown()


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


BALANCE_429 = (
    "Error code: 429 - {'error': {'code': '1113', 'message': "
    "'Insufficient balance or no resource package. Please recharge.'}}"
)


class EmptyWalletClient(FakeClient):
    """Paid GLM models refuse; the free one still answers."""

    def __init__(self):
        super().__init__("glm-4.5-flash")

        completions = self.chat.completions

        class PaidCompletions:
            def create(self, **kwargs):

                completions.outer.asked.append(kwargs["model"])

                if kwargs["model"] != "glm-4.5-flash":
                    raise RuntimeError(BALANCE_429)

                return FakeReply("Free answer", kwargs["model"])

        self.chat.completions = PaidCompletions()


def test_an_empty_wallet_is_not_retried_on_every_message(monkeypatch):
    provider = build()
    client = EmptyWalletClient()
    provider.client = client

    first = provider.chat("hi")
    asked_at_first = list(client.asked)
    client.asked.clear()

    second = provider.chat("hi again")

    assert first["success"] is True and second["success"] is True
    assert len(asked_at_first) > 1, "the paid models were tried while the answer was unknown"
    assert client.asked == ["glm-4.5-flash"], "the empty wallet was tried again"


def test_vision_skips_the_doomed_request_while_the_wallet_is_empty(tmp_path):
    provider = build()
    client = EmptyWalletClient()
    provider.client = client

    provider.chat("hi")
    client.asked.clear()

    image = tmp_path / "shot.png"
    image.write_bytes(b"fake-png")

    result = provider.see("what is on my screen?", str(image))

    assert result["success"] is False
    assert "recharge" in result["error"]
    assert client.asked == []
