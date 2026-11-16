import pytest

from providers import zai
from providers.zai import ZaiProvider


@pytest.fixture(autouse=True)
def empty_wallet_forgotten():
    """A wallet state must never leak from one test to the next."""

    zai.PROBE_ENABLED = False

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


def build(working_model="glm-4.7-flash"):
    provider = ZaiProvider.__new__(ZaiProvider)

    provider.provider_name = "zai"
    provider.api_key = "test-key"
    provider.model = "glm-4.7-flash"
    provider._working = None
    provider.client = FakeClient(working_model)

    return provider


def test_missing_key_is_reported(monkeypatch):
    monkeypatch.delenv("ZAI_API_KEY", raising=False)

    provider = ZaiProvider()

    assert provider.health() is False
    assert provider.chat("hi")["success"] is False


def test_the_free_model_answers_first():
    provider = build("glm-4.7-flash")

    result = provider.chat("hi")

    assert result["success"] is True
    assert result["provider"] == "zai"
    assert result["response"] == "Hello from GLM"
    assert provider._working == "glm-4.7-flash"


def test_the_free_model_is_tried_before_a_paid_one():
    provider = build("glm-4.7")

    result = provider.chat("hi")

    assert result["success"] is True
    assert result["model"] == "glm-4.7"
    assert provider.client.asked[0] == "glm-4.7-flash", "a paid model went first"
    assert "glm-4.7" in provider.client.asked[1:], "the paid fallback was never asked"


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
        super().__init__("glm-4.7-flash")

        completions = self.chat.completions

        class PaidCompletions:
            def create(self, **kwargs):

                completions.outer.asked.append(kwargs["model"])

                if kwargs["model"] not in ("glm-4.7-flash", "glm-4.6v-flash"):
                    raise RuntimeError(BALANCE_429)

                return FakeReply("Free answer", kwargs["model"])

        self.chat.completions = PaidCompletions()


def test_a_timed_out_free_model_marks_zai_slow():
    class SlowClient(FakeClient):
        def __init__(self):
            super().__init__("nothing")

            completions = self.chat.completions

            class Timeout:
                def create(self, **kwargs):
                    raise TimeoutError("Request timed out.")

            self.chat.completions = Timeout()

    provider = build()
    provider.client = SlowClient()

    assert zai.slow() is False

    result = provider.chat("hi")

    assert result["success"] is False
    assert zai.slow() is True, "the next reply would wait on a slow model again"


def test_paid_models_are_never_asked_without_a_balance():
    provider = build()
    client = EmptyWalletClient()
    provider.client = client

    first = provider.chat("hi")
    second = provider.chat("hi again")

    assert first["success"] is True and second["success"] is True
    assert client.asked == ["glm-4.7-flash", "glm-4.7-flash"], "a paid model was tried"


def test_the_free_vision_model_answers_while_the_wallet_is_empty(tmp_path):
    provider = build()
    client = EmptyWalletClient()
    provider.client = client

    image = tmp_path / "shot.png"
    image.write_bytes(b"fake-png")

    result = provider.see("what is on my screen?", str(image))

    assert result["success"] is True
    assert client.asked == ["glm-4.6v-flash"]
