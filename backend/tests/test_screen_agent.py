import json
from pathlib import Path

from tools import screen_agent


class ScriptedVision:
    """A vision model that answers from a fixed list of plans."""

    calls = []
    replies = []

    def __init__(self):
        pass

    def health(self):
        return True

    def see(self, question, image_path):
        ScriptedVision.calls.append(question)

        reply = ScriptedVision.replies.pop(0)

        if isinstance(reply, dict):
            return {"success": True, "model": "glm-4.6v-flash", "answer": json.dumps(reply)}

        return {"success": False, "error": reply}


def patch_environment(monkeypatch, replies, tmp_path):
    shot = tmp_path / "shot.png"
    shot.write_bytes(b"png")

    ScriptedVision.replies = list(replies)
    ScriptedVision.calls = []

    monkeypatch.setattr(
        screen_agent.screen_reader.screenshot,
        "capture_screen",
        lambda label="", persist=True: {"success": True, "path": str(shot)},
    )
    monkeypatch.setattr(
        screen_agent.screen_reader, "shrink", lambda path: Path(path)
    )
    monkeypatch.setattr(
        screen_agent.screen_reader.vision,
        "see",
        lambda question, image_path: ScriptedVision().see(question, image_path),
    )
    monkeypatch.setattr(screen_agent, "show_arrow", lambda *a, **k: None)
    monkeypatch.setattr(screen_agent.time, "sleep", lambda *a, **k: None)


def test_json_survives_code_fences_and_chatter():
    raw = 'Sure, here it is:\n```json\n{"action": "click", "x": 10, "y": 20}\n```'

    assert screen_agent._extract_json(raw)["x"] == 10
    assert screen_agent._extract_json('```\n{"action":"done"}\n```')["action"] == "done"
    assert screen_agent._extract_json("no json here") is None


def test_agent_clicks_then_finishes(monkeypatch, tmp_path):
    patch_environment(
        monkeypatch,
        [
            {"thought": "Search bar dikh raha hai", "action": "click", "x": 100, "y": 200},
            {"thought": "Kaam ho gaya", "action": "done", "text": "Search box ready hai."},
        ],
        tmp_path,
    )

    monkeypatch.setattr(screen_agent, "click", lambda x, y: {"action": "click", "x": x, "y": y})

    result = screen_agent.run_task("search python")

    assert result["success"] is True
    assert result["finished"] is True
    assert result["steps"][0]["action"] == "click"
    assert result["steps"][0]["detail"]["x"] == 100
    assert result["answer"] == "Search box ready hai."


def test_agent_types_text(monkeypatch, tmp_path):
    patch_environment(
        monkeypatch,
        [
            {"thought": "Field mil gaya", "action": "type", "text": "hello"},
            {"thought": "done", "action": "done"},
        ],
        tmp_path,
    )

    typed = []

    monkeypatch.setattr(screen_agent, "type_text", lambda text: typed.append(text) or {"action": "type"})

    screen_agent.run_task("type hello")

    assert typed == ["hello"]


def test_answer_only_goal_returns_the_answer(monkeypatch, tmp_path):
    patch_environment(
        monkeypatch,
        [{"thought": "Page about Python", "action": "answer", "text": "Python ka docs page hai."}],
        tmp_path,
    )

    result = screen_agent.run_task("yeh page kya hai")

    assert result["success"] is True
    assert "docs page" in result["answer"]


def test_a_dead_vision_model_is_explained(monkeypatch, tmp_path):
    patch_environment(
        monkeypatch,
        ["Error code: 429 - {'message': 'Insufficient balance'}"],
        tmp_path,
    )

    result = screen_agent.run_task("click login")

    assert result["success"] is False
    assert "no free vision model" in result["error"].lower()


def test_narration_lists_each_step():
    result = {
        "answer": "Login button mil gaya.",
        "steps": [
            {"step": 1, "thought": "Login button dikh raha hai", "action": "click"},
            {"step": 2, "thought": "Kaam poora", "action": "done"},
        ],
    }

    text = screen_agent.narrate(result)

    assert "1. Login button dikh raha hai — click kiya" in text
    assert "Login button mil gaya." in text


def test_dry_run_does_not_touch_the_mouse(monkeypatch, tmp_path):
    patch_environment(
        monkeypatch,
        [
            {"thought": "button", "action": "click", "x": 5, "y": 5},
            {"thought": "done", "action": "done"},
        ],
        tmp_path,
    )

    called = []

    monkeypatch.setattr(screen_agent, "click", lambda x, y: called.append((x, y)))

    result = screen_agent.run_task("click", dry_run=True)

    assert called == []
    assert result["steps"][0]["detail"]["dry_run"] is True
