"""The real tool-calling loop.

Model asks for a tool -> we run it -> the result goes back to the model -> the
model either calls another tool or answers. "Confirm" tools park the loop until
the user says yes.
"""

import json

from tools.approvals import describe


MAX_STEPS = 5

MAX_RESULT_CHARS = 4000

TOOL_GUIDE = """
You can use tools when the request needs real actions instead of words.

Rules:
- Call at most one or two tools per step and only when they are needed.
- Never invent file contents or command output; call the tool.
- Never look at the screen, read it or take a screenshot unless the user asks.
- If a task needs facts you do not have (a party's date or place, a name), ask
  one short question first; never invent them, and never send a message the
  user has not seen.
- Paths are relative to the workspace root.
- run_command and write_file ask the user for confirmation first.
- After the tool results arrive, answer the user in plain language.
"""


class AgentLoop:

    def __init__(self, ai, registry, executor, approvals):

        self.ai = ai

        self.registry = registry

        self.executor = executor

        self.approvals = approvals

    def _messages(self, message, system_prompt, history=""):

        system = (system_prompt or "").strip() + "\n" + TOOL_GUIDE

        if history:

            system += "\nRecent conversation:\n" + history

        return [
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ]

    def run(self, message, system_prompt="", history=""):

        if not self.registry.all():

            return None

        messages = self._messages(message, system_prompt, history)

        tools = self.registry.schemas()

        steps = []

        for _ in range(MAX_STEPS):

            response = self.ai.chat_with_tools(messages, tools)

            if not response or not response.get("success"):

                return None

            calls = response.get("tool_calls") or []

            if not calls:

                content = (response.get("content") or "").strip()

                if not content:

                    return None

                return {
                    "success": True,
                    "provider": response.get("provider", "ai"),
                    "response": content,
                    "steps": steps,
                    "needs_confirmation": False,
                }

            messages.append(response["message"])

            for call in calls:

                tool = self.registry.get(call["name"])

                if tool is None:

                    messages.append({
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": json.dumps({
                            "success": False,
                            "error": f"Unknown tool: {call['name']}",
                        }),
                    })

                    continue

                if tool["permission"] == "confirm":

                    pending = self.approvals.request(
                        call["name"],
                        call["arguments"],
                        reason=(
                            "This tool runs on your computer and can change "
                            "things."
                        ),
                    )

                    return {
                        "success": True,
                        "provider": response.get("provider", "ai"),
                        "response": describe(pending),
                        "steps": steps,
                        "pending": pending,
                        "needs_confirmation": True,
                    }

                result = self.executor.execute(
                    call["name"],
                    **call["arguments"],
                )

                steps.append({
                    "tool": call["name"],
                    "arguments": call["arguments"],
                    "success": bool(result.get("success")),
                })

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(
                        result,
                        default=str,
                    )[:MAX_RESULT_CHARS],
                })

        return {
            "success": True,
            "provider": "agent",
            "response": (
                "I ran out of tool steps before finishing. Here is what I did: "
                + ", ".join(step["tool"] for step in steps)
            ),
            "steps": steps,
            "needs_confirmation": False,
        }
