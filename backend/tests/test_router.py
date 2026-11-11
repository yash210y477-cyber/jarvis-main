from brain.router import Router
from memory.memory import Memory
from memory.storage import Storage


def make_router(tmp_path):

    storage = Storage(str(tmp_path / "router.db"))

    return Router(Memory(storage))


def test_remember_multiple_facts(tmp_path):

    router = make_router(tmp_path)

    result = router.route(
        {
            "intent": "remember",
            "text": "",
            "entities": [
                {"field": "name", "value": "Yash"},
                {"field": "city", "value": "Delhi"},
            ],
        }
    )

    assert result["success"] is True

    assert "name" in result["message"]

    assert "city" in result["message"]

    assert len(result["remembered"]) == 2


def test_recall_specific_field(tmp_path):

    router = make_router(tmp_path)

    router.route(
        {
            "intent": "remember",
            "text": "",
            "entities": [{"field": "name", "value": "Yash"}],
        }
    )

    result = router.route({"intent": "recall", "text": "what is my name"})

    assert result["success"] is True

    assert result["message"] == "Your name is Yash."


def test_recall_all_returns_readable_text(tmp_path):

    router = make_router(tmp_path)

    router.route(
        {
            "intent": "remember",
            "text": "",
            "entities": [
                {"field": "name", "value": "Yash"},
                {"field": "bike", "value": "Classic 350"},
            ],
        }
    )

    result = router.route(
        {"intent": "recall", "text": "what do you remember"}
    )

    assert "Here is what I remember" in result["message"]

    assert "- name: Yash" in result["message"]

    assert "- bike: Classic 350" in result["message"]


def test_recall_unknown_field(tmp_path):

    router = make_router(tmp_path)

    result = router.route({"intent": "recall", "text": "what is my email"})

    assert result["success"] is True

    assert "don't know your email" in result["message"]
