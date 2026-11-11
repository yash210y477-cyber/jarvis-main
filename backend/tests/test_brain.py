from brain.brain import Brain


def test_summary_never_blocks_without_providers(monkeypatch):

    brain = Brain(summary_threshold=1, conversation_keep=2)

    monkeypatch.setattr(brain.ai, "providers", [])

    brain.memory.add_user_message("hello")

    brain.memory.add_assistant_message("hi")

    # Must return immediately instead of calling seven dead providers.
    brain._maybe_summarize()

    assert brain.memory.message_count() >= 2


def test_router_memory_works_without_ai(monkeypatch):

    brain = Brain(summary_threshold=1000)

    monkeypatch.setattr(brain.ai, "providers", [])

    saved = brain.chat("my name is MemoryUser and my city is Pune")

    assert saved["success"] is True

    recalled = brain.chat("what is my name")

    assert recalled["response"] == "Your name is MemoryUser."

    city = brain.chat("where do i live")

    assert city["response"] == "You live in Pune."
