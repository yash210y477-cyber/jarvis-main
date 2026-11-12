"""Semantic memory: embed text, then find it by meaning (no API key)."""

import numpy as np
import pytest

from memory import semantic as semantic_module
from memory.semantic import HashingEmbedder, SemanticMemory
from memory.storage import Storage


class FakeEmbedder:
    """Tiny deterministic stand-in, so tests never download a model."""

    def __init__(self, name="fake-v1", dim=4):
        self.name = name
        self.dim = dim

    def encode(self, texts):
        rows = []
        for text in texts:
            low = (text or "").lower()
            vector = np.array([
                1.0 if any(word in low for word in (
                    "react", "ai", "jarvis", "project", "assistant"
                )) else 0.0,
                1.0 if any(word in low for word in (
                    "python", "fastapi", "backend"
                )) else 0.0,
                1.0 if "pizza" in low else 0.0,
                0.15,
            ], dtype=np.float32)
            if self.dim == 3:
                vector = vector[:3]
            norm = float(np.linalg.norm(vector))
            rows.append(vector / norm if norm else vector)
        return np.asarray(rows, dtype=np.float32)


def make_memory(tmp_path, embedder=None, name="memory.db"):

    path = tmp_path / name

    storage = Storage(path=path)

    return SemanticMemory(
        storage=storage,
        embedder=embedder or FakeEmbedder(),
        path=path,
    )


def test_search_finds_meaning_not_keywords(tmp_path):

    memory = make_memory(tmp_path)

    memory.index("User is developing a React-based AI assistant named JARVIS.", "note")
    memory.index("I like eating pizza.", "note")
    memory.index("The backend is built with Python FastAPI.", "note")

    results = memory.search("mera AI desktop project")

    assert results
    assert "React-based AI assistant" in results[0]["text"]
    assert all("pizza" not in item["text"] for item in results)
    assert results[0]["score"] > 0.5


def test_same_text_is_stored_once(tmp_path):

    memory = make_memory(tmp_path)

    assert memory.index("User likes dark mode.", "note") is True
    assert memory.index("User likes dark mode.", "note") is False
    assert memory.stats()["documents"] == 1


def test_unrelated_text_stays_below_the_threshold(tmp_path):

    memory = make_memory(tmp_path)

    memory.index("I like eating pizza.", "note")

    assert memory.search("what is my backend stack") == []


def test_sync_indexes_profile_facts_notes_and_messages(tmp_path):

    path = tmp_path / "sync.db"

    storage = Storage(path=path)

    storage.set_profile("name", "Yash")
    storage.set_fact("editor", "VS Code")
    storage.add_note("Project JARVIS uses React and FastAPI.")
    storage.add_message("user", "backend FastAPI me bana hua hai yaar")

    memory = SemanticMemory(storage=storage, embedder=FakeEmbedder(), path=path)

    added = memory.sync()

    assert added >= 4

    found = memory.search("mera project kis stack par hai")

    assert any("React and FastAPI" in item["text"] for item in found)

    # Nothing new the second time.
    assert memory.sync() == 0


def test_model_change_rebuilds_vectors(tmp_path):

    path = tmp_path / "switch.db"

    storage = Storage(path=path)

    first = SemanticMemory(
        storage=storage, embedder=FakeEmbedder("fake-v1", 4), path=path
    )

    first.index("User is developing a React-based AI assistant.", "note")
    first.index("Backend is Python FastAPI.", "note")
    first.close()

    second = SemanticMemory(
        storage=storage, embedder=FakeEmbedder("fake-v2", 3), path=path
    )

    results = second.search("mera ai project")

    assert results
    assert results[0]["source"] == "note"
    assert second.stats()["documents"] == 2
    assert second.stats()["model"] == "fake-v2"


def test_hashing_embedder_is_stable_and_normalised():

    embedder = HashingEmbedder()

    first = embedder.encode(["I am developing JARVIS"])[0]
    again = embedder.encode(["I am developing JARVIS"])[0]
    other = embedder.encode(["I like eating pizza"])[0]

    assert np.allclose(first, again)
    assert not np.allclose(first, other)
    assert first.size == embedder.dim
    assert float(np.linalg.norm(first)) == pytest.approx(1.0, rel=1e-5)


def test_search_is_quiet_before_warm_up(monkeypatch):

    monkeypatch.setattr(semantic_module, "_READY", semantic_module.threading.Event())

    assert semantic_module.search_memory("mera project") == []


def test_context_asks_for_hinglish_and_relevant_memory():

    from memory.context import ContextBuilder
    from memory.manager import MemoryManager

    prompt = ContextBuilder(MemoryManager()).build("mera AI project kya tha")

    assert "### Reply Language" in prompt
    assert "Hinglish" in prompt
    assert "### Current User Message" in prompt

def test_junk_messages_are_not_indexed(tmp_path):

    from memory.semantic import SemanticMemory

    assert SemanticMemory.worth_indexing("ALL AI PROVIDER FAILED") is False
    assert SemanticMemory.worth_indexing("open chrome", "user") is False
    assert SemanticMemory.worth_indexing("search bahubali", "user") is False
    assert SemanticMemory.worth_indexing("User builds JARVIS with React.") is True

    path = tmp_path / "junk.db"

    storage = Storage(path=path)

    storage.add_message("assistant", "ALL AI PROVIDER FAILED")
    storage.add_message("user", "open chrome")
    storage.add_message("user", "User builds JARVIS with React and FastAPI.")

    memory = SemanticMemory(storage=storage, embedder=FakeEmbedder(), path=path)

    memory.sync()

    assert memory.stats()["documents"] == 1


def test_old_index_is_migrated_away(tmp_path):

    memory = make_memory(tmp_path)

    memory.index("User is developing a React-based AI assistant.", "note")

    assert memory.migrate() is True
    assert memory.stats()["documents"] == 0
    assert memory.migrate() is False
