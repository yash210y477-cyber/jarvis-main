"""The real tool-calling loop.

Model asks for a tool -> we run it -> the result goes back to the model -> the
model either calls another tool or answers. "Confirm" tools park the loop until
the user says yes.
"""

import json
import re

from tools.approvals import describe


MAX_STEPS = 5

MAX_RESULT_CHARS = 4000

# A pasted code block cannot be downloaded, so the model is asked once to put it
# in a file instead of into the reply.
CODE_BLOCK = re.compile(r"```[\s\S]+?```")
CREATE_WORDS = re.compile(
    r"\b(write|create|make|save|build|generate|banao|bana|banaao|likho|likh)\b",
    re.IGNORECASE,
)
FILE_WORDS = re.compile(
    r"\b(file|files|script|program|game|app|application|project|code|page|website)\b",
    re.IGNORECASE,
)
FILE_NUDGE = (
    "Don't paste the code into the reply: the user cannot download a code block. "
    "Call write_file now with a sensible file name and the complete code, then "
    "answer in one short line."
)


def wants_a_file(message: str) -> bool:
    """True when the request is asking for a program or file, not an explanation."""

    return bool(CREATE_WORDS.search(message) and FILE_WORDS.search(message))

TOOL_GUIDE = """
You can use tools when the request needs real actions instead of words.

Rules:
- Call at most one or two tools per step and only when they are needed.
- Never invent file contents or command output; call the tool.
- Never look at the screen, read it or take a screenshot unless the user asks.
  If the screen would help, say so in one line and let the user decide; the
  screen tools ask for permission before they capture anything.
- If a task needs facts you do not have (a party's date or place, a name), ask
  one short question first; never invent them, and never send a message the
  user has not seen.
- Paths are relative to the workspace root.
- When the user asks for a program, page, script or any file, write it with
  write_file instead of pasting the code into the reply: the chat shows the
  file with a Download button. Keep the reply to what you made and how to run it.
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
        nudged = False

        for _ in range(MAX_STEPS):

            response = self.ai.chat_with_tools(messages, tools)

            if not response or not response.get("success"):

                return None

            calls = response.get("tool_calls") or []

            if not calls:

                content = (response.get("content") or "").strip()

                if (
                    content
                    and not nudged
                    and wants_a_file(message)
                    and CODE_BLOCK.search(content)
                ):

                    nudged = True

                    messages.append({"role": "assistant", "content": content})

                    messages.append({"role": "system", "content": FILE_NUDGE})

                    continue

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
