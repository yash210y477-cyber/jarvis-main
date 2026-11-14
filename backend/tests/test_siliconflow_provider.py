from providers.siliconflow import SiliconFlowProvider


class FakeMessage:
    def __init__(self, content):
        self.content = content
        self.tool_calls = None


class FakeReply:
    def __init__(self, content, model):
        self.choices = [type("Choice", (), {"message": FakeMessage(content)})()]
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

                return FakeReply("Hello from SiliconFlow", model)

        self.chat = type("Chat", (), {})()
        self.chat.completions = Completions(self)


def build(working_model="deepseek-ai/DeepSeek-V4.1-Flash"):
    provider = SiliconFlowProvider.__new__(SiliconFlowProvider)

    provider.provider_name = "siliconflow"
    provider.api_key = "test-key"
    provider.model = "deepseek-ai/DeepSeek-V4.1-Flash"
    provider._working = None
    provider.client = FakeClient(working_model)

    return provider


def test_missing_key_is_reported(monkeypatch):
    monkeypatch.delenv("SILICONFLOW_API_KEY", raising=False)

    provider = SiliconFlowProvider()

    assert provider.health() is False
    assert provider.chat("hi")["success"] is False


def test_preferred_model_answers():
    provider = build()

    result = provider.chat("hi")

    assert result["success"] is True
    assert result["provider"] == "siliconflow"
    assert result["response"] == "Hello from SiliconFlow"


def test_unavailable_model_falls_through():
    provider = build("zai-org/GLM-5.3-Flash")

    result = provider.chat("hi")

    assert result["success"] is True
    assert result["model"] == "zai-org/GLM-5.3-Flash"
    assert provider._working == "zai-org/GLM-5.3-Flash"


def test_nothing_answering_returns_the_error():
    provider = build("nothing")

    result = provider.chat("hi")

    assert result["success"] is False
    assert "model not available" in result["error"]
