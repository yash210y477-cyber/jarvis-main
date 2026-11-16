"""The priority list comes from measurements, so it can be tested like data."""

import json
import time

import pytest

from providers import ranking
from providers.manager import AIManager


@pytest.fixture
def measured(tmp_path, monkeypatch):
    path = tmp_path / "model_ranking.json"

    rows = {
        "text": [
            {"provider": "groq", "model": "openai/gpt-oss-120b", "quality": 5, "seconds": 2.9, "error": ""},
            {"provider": "zai", "model": "glm-4.7-flash", "quality": 5, "seconds": 60.2, "error": ""},
            {"provider": "openrouter", "model": "openrouter/free", "quality": 5, "seconds": 42.3, "error": ""},
            {"provider": "ollama", "model": "qwen2.5:3b", "quality": 4, "seconds": 7.6, "error": ""},
            {"provider": "openrouter", "model": "google/gemma-4-31b-it:free", "quality": 0, "seconds": 0.0, "error": "RateLimitError"},
        ],
        "vision": [
            {"provider": "zai", "model": "glm-4.6v-flash", "quality": 1, "seconds": 1.2, "error": ""},
            {"provider": "openrouter", "model": "inclusionai/ling-3.2-flash:free", "quality": 1, "seconds": 4.1, "error": ""},
        ],
        "measured": time.time(),
    }

    path.write_text(json.dumps(rows), encoding="utf-8")
    monkeypatch.setattr(ranking, "_file", lambda: path)

    return path


def test_the_best_quality_then_the_fastest_comes_first(measured):
    order = ranking.models("text")

    assert order[0] == ("groq", "openai/gpt-oss-120b")
    assert order[1] == ("openrouter", "openrouter/free")
    assert order[2] == ("zai", "glm-4.7-flash")
    assert order[-1] == ("ollama", "qwen2.5:3b")


def test_a_model_that_errored_is_never_offered(measured):
    assert ("openrouter", "google/gemma-4-31b-it:free") not in ranking.models("text")


def test_providers_follow_their_best_model(measured):
    assert ranking.providers("text") == ["groq", "openrouter", "zai", "ollama"]


def test_a_stale_ranking_leaves_the_configured_order_alone(tmp_path, monkeypatch):
    path = tmp_path / "old.json"
    path.write_text(
        json.dumps({"text": [], "measured": time.time() - 30 * 86400}), encoding="utf-8"
    )
    monkeypatch.setattr(ranking, "_file", lambda: path)

    assert ranking.models("text") == []
    assert ranking.providers("text") == []


def test_without_a_benchmark_nothing_is_reordered(tmp_path, monkeypatch):
    monkeypatch.setattr(ranking, "_file", lambda: tmp_path / "missing.json")

    manager = AIManager.__new__(AIManager)

    class Fake:
        def __init__(self, name):
            self._name = name

        def name(self):
            return self._name

    providers = [Fake("zai"), Fake("groq")]
    manager.providers = providers

    assert [item.name() for item in manager._by_measured_speed(providers)] == ["zai", "groq"]


def test_the_best_measured_model_is_the_one_asked(measured):
    manager = AIManager.__new__(AIManager)

    assert manager.model_for("groq", "general") == "openai/gpt-oss-120b"
    assert manager.model_for("zai", "general") == "glm-4.7-flash"


def test_priority_lists_every_task_and_its_free_models(measured):
    class Fake:
        def __init__(self, name, models):
            self._name = name
            self._models = models

        def name(self):
            return self._name

        def free_models(self, first=None):
            return list(dict.fromkeys([first, *self._models])) if first else list(self._models)

    manager = AIManager.__new__(AIManager)
    manager.providers = [
        Fake("ollama", ["qwen2.5:3b"]),
        Fake("openrouter", ["openrouter/free", "google/gemma-4-31b-it:free"]),
        Fake("groq", ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"]),
        Fake("zai", ["glm-4.7-flash"]),
    ]

    tasks = manager.priority()["tasks"]

    assert set(tasks) == {"chat", "coding", "research", "vision"}
    # Coding starts at the measured winner; the rest of its free models follow.
    assert tasks["coding"][0] == {"provider": "groq", "model": "openai/gpt-oss-120b"}
    assert {"provider": "groq", "model": "qwen/qwen3.8-27b"} in tasks["coding"]
    # Research still asks OpenRouter's web-aware model, in its measured place.
    assert {
        "provider": "openrouter",
        "model": "openrouter/auto:online",
    } in tasks["research"]
    # Vision is the free z.ai model, then the free OpenRouter ones.
    assert tasks["vision"][0] == {"provider": "zai", "model": "glm-4.6v-flash"}
    assert {
        "provider": "openrouter",
        "model": "inclusionai/ling-3.2-flash:free",
    } in tasks["vision"]


def test_the_manager_puts_the_measured_winner_first(measured):
    class Fake:
        def __init__(self, name):
            self._name = name

        def name(self):
            return self._name

    manager = AIManager.__new__(AIManager)
    manager.providers = [Fake("ollama"), Fake("zai"), Fake("groq"), Fake("openrouter")]

    order = manager._by_measured_speed(manager.providers)

    assert [item.name() for item in order] == ["groq", "openrouter", "zai", "ollama"]
