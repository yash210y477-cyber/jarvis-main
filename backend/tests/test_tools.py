import json
from pathlib import Path

import pytest

from config.settings import settings

from tools import builtin, local_intents, shell
from tools.agent import AgentLoop
from tools.approvals import ApprovalStore, describe, is_approval, is_rejection
from tools.executor import ActionExecutor
from tools.registry import CONFIRM, ToolRegistry


@pytest.fixture()
def workspace(tmp_path, monkeypatch):

    monkeypatch.setattr(settings, "WORKSPACE_ROOT", str(tmp_path))

    return tmp_path


def test_registry_exposes_openai_schemas():

    schemas = builtin.REGISTRY.schemas()

    names = {entry["function"]["name"] for entry in schemas}

    assert {"list_files", "read_file", "screenshot", "media_control"} <= names
    assert all(entry["type"] == "function" for entry in schemas)

    read = next(
        entry for entry in schemas
        if entry["function"]["name"] == "read_file"
    )

    assert read["function"]["parameters"]["required"] == ["path"]


def test_destructive_tools_need_confirmation():

    assert builtin.REGISTRY.get("run_command")["permission"] == CONFIRM
    assert builtin.REGISTRY.get("write_file")["permission"] == CONFIRM
    assert builtin.REGISTRY.get("screenshot")["permission"] != CONFIRM


def test_files_stay_inside_the_workspace(workspace):

    written = builtin.REGISTRY.get("write_file")["handler"](
        "notes.txt",
        "hello",
    )

    assert written["success"] is True
    assert (workspace / "notes.txt").read_text(encoding="utf-8") == "hello"

    read = builtin.REGISTRY.get("read_file")["handler"]("notes.txt")

    assert read["success"] is True
    assert read["content"] == "hello"

    assert builtin.REGISTRY.get("read_file")["handler"]("../secret.txt")["success"] is False
    assert builtin.REGISTRY.get("list_files")["handler"]("C:/Windows")["success"] is False
    assert builtin.REGISTRY.get("list_files")["handler"](".venv")["success"] is False


def test_shell_allowlist_and_blocklist(workspace):

    denied = shell.run_command("format C:")

    assert denied["success"] is False
    assert "allowlist" in denied["error"].lower()

    assert shell.run_command("powershell -enc ZWNobyBoaQ==")["success"] is False

    ok = shell.run_command("echo hello")

    assert ok["success"] is True
    assert "hello" in ok["stdout"]


def test_approval_store_round_trip():

    store = ApprovalStore()

    pending = store.request("run_command", {"command": "git status"})

    assert pending["id"]
    assert "git status" in describe(pending)

    assert store.peek()["tool"] == "run_command"
    assert store.take()["tool"] == "run_command"
    assert store.peek() is None

    assert is_approval("yes") and is_approval("haan kar do")
    assert is_rejection("no") and is_rejection("cancel")
    assert not is_approval("what is my name")


def test_local_intents_for_tools_without_ai():

    assert local_intents.detect("take a screenshot")["tool"] == "screenshot"
    assert local_intents.detect("pause the music")["arguments"]["action"] == "play_pause"
    assert local_intents.detect("volume up")["arguments"]["action"] == "volume_up"

    timer = local_intents.detect("set a timer for 5 minutes")

    assert timer["tool"] == "set_timer"
    assert timer["arguments"]["seconds"] == 300

    assert local_intents.detect("list files in backend")["arguments"]["path"] == "backend"
    assert local_intents.detect("run git status")["tool"] == "run_command"
    assert local_intents.detect("what is my name") is None


def test_local_intents_do_not_hijack_chat():

    for message in ("hey", "what is the time", "who am i", "play despacito for me"):

        intent = local_intents.detect(message)

        assert intent is None or intent["tool"] != "media_control"


class FakeAI:

    """A provider that asks for one tool, then answers."""

    def __init__(self, calls):

        self.calls = list(calls)

    def chat_with_tools(self, messages, tools):

        if self.calls:

            name, arguments = self.calls.pop(0)

            return {
                "success": True,
                "provider": "fake",
                "message": {
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(arguments),
                        },
                    }],
                },
                "tool_calls": [{"id": "call-1", "name": name, "arguments": arguments}],
                "content": "",
            }

        tool_messages = [m for m in messages if m["role"] == "tool"]

        return {
            "success": True,
            "provider": "fake",
            "message": {"role": "assistant", "content": "done"},
            "tool_calls": [],
            "content": f"done after {len(tool_messages)} tool result(s)",
        }


def test_agent_loop_executes_tool_and_feeds_result_back(workspace):

    (workspace / "readme.md").write_text("hello agent", encoding="utf-8")

    loop = AgentLoop(
        FakeAI([("read_file", {"path": "readme.md"})]),
        builtin.REGISTRY,
        ActionExecutor(builtin.REGISTRY),
        ApprovalStore(),
    )

    result = loop.run("read readme.md", "You are JARVIS.")

    assert result["success"] is True
    assert result["response"] == "done after 1 tool result(s)"
    assert result["steps"][0]["tool"] == "read_file"
    assert result["needs_confirmation"] is False


def test_agent_loop_parks_confirm_tools(workspace):

    approvals = ApprovalStore()

    loop = AgentLoop(
        FakeAI([("run_command", {"command": "git status"})]),
        builtin.REGISTRY,
        ActionExecutor(builtin.REGISTRY),
        approvals,
    )

    result = loop.run("run git status", "You are JARVIS.")

    assert result["needs_confirmation"] is True
    assert "git status" in result["response"]
    assert result["pending"]["tool"] == "run_command"
    assert approvals.peek()["tool"] == "run_command"
