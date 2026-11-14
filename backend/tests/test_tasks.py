from types import SimpleNamespace

from brain import tasks
from providers.manager import AIManager


def test_coding_messages_are_detected():
    assert tasks.detect("write a python function to reverse a list") == "coding"
    assert tasks.detect("fix this error in my react code") == "coding"
    assert tasks.detect("code likho for sorting") == "coding"


def test_research_messages_are_detected():
    assert tasks.detect("latest news about ai chips") == "research"
    assert tasks.detect("compare iphone and pixel") == "research"
    assert tasks.detect("batao detail me quantum computing ke baare me") == "research"


def test_plain_chat_stays_general():
    assert tasks.detect("how are you doing") == "general"
    assert tasks.detect("open spotify") == "general"
    assert tasks.detect("") == "general"


class FakeProvider:
    def __init__(self, name, answer):
        self._name = name
        self.answer = answer
        self.asked = []

    def name(self):
        return self._name

    def chat(self, prompt, model=None):
        self.asked.append(model)
        return {"success": True, "provider": self._name, "response": self.answer}


def build_manager():
    manager = AIManager.__new__(AIManager)

    manager.providers = [
        FakeProvider("cerebras", "cerebras answer"),
        FakeProvider("groq", "groq answer"),
        FakeProvider("openrouter", "openrouter answer"),
        FakeProvider("ollama", "local answer"),
    ]

    return manager


def test_coding_prefers_groq_and_openrouter():
    manager = build_manager()

    result = manager.chat("write a python function", task="coding")

    assert result["provider"] == "groq"


def test_research_prefers_openrouter_and_asks_online():
    manager = build_manager()

    result = manager.chat("latest news about ai", task="research")

    assert result["provider"] == "openrouter"

    openrouter = manager.find("openrouter")

    assert openrouter.asked[-1].endswith(":online")


def test_a_chosen_provider_still_wins():
    manager = build_manager()

    result = manager.chat("write a python function", provider="cerebras", task="coding")

    assert result["provider"] == "cerebras"


def test_priority_list_runs_from_cloud_to_local():
    from config.settings import settings

    assert settings.PROVIDER_PRIORITY == [
        "zai",
        "openrouter",
        "groq",
        "deepseek",
        "siliconflow",
        "cerebras",
        "ollama",
    ]


def test_manager_keeps_the_priority_order():
    from providers.manager import AIManager

    assert [p.name() for p in AIManager().providers] == [
        "zai",
        "openrouter",
        "groq",
        "deepseek",
        "siliconflow",
        "cerebras",
        "ollama",
    ]
