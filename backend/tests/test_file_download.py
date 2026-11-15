"""A generated file is offered in the chat and only copied to Downloads on request."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from config.settings import settings
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    from main import app

    return TestClient(app)


def test_a_written_file_can_be_fetched_without_touching_downloads(client, tmp_path):
    (tmp_path / "chess.py").write_text("print('hi')", encoding="utf-8")

    body = client.get("/files/chess.py")

    assert body.status_code == 200
    assert "print('hi')" in body.text
    assert not (tmp_path / "Downloads").exists()


def test_download_copies_the_file_into_downloads_jarvis(client, tmp_path):
    (tmp_path / "chess.py").write_text("print('hi')", encoding="utf-8")

    result = client.post("/files/chess.py/download").json()

    target = tmp_path / "Downloads" / "Jarvis" / "chess.py"

    assert result["success"] is True
    assert Path(result["path"]) == target
    assert target.read_text(encoding="utf-8") == "print('hi')"


def test_a_path_outside_the_workspace_is_refused(client):
    assert client.get("/files/..%2F..%2Fsecret.txt").status_code in (400, 404)


def test_a_written_file_becomes_one_chat_marker():
    from brain.brain import file_markers

    steps = [
        {"tool": "write_file", "arguments": {"path": "chess game.py"}, "success": True},
        {"tool": "run_command", "arguments": {"command": "ls"}, "success": True},
        {"tool": "write_file", "arguments": {"path": "broken.py"}, "success": False},
    ]

    assert file_markers(steps) == ["[file]chess%20game.py"]


def test_only_a_request_for_a_program_gets_the_nudge():
    from tools.agent import wants_a_file

    assert wants_a_file("create a chess game with python")
    assert wants_a_file("ek python file banao jo chess khele")

    assert not wants_a_file("explain this code")
    assert not wants_a_file("what is the weather")
