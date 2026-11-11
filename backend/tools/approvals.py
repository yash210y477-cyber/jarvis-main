"""Pending confirmations for destructive tools.

A single local user talks to JARVIS, so one pending action at a time is enough.
The agent loop parks a "confirm" tool call here, tells the user what it wants to
run, and executes it only when the next message is an approval.
"""

import threading
import time
import uuid


TTL_SECONDS = 300

APPROVALS = {"yes", "y", "yeah", "yep", "ok", "okay", "sure", "confirm",
             "do it", "haan", "ha", "han", "kar do", "kardo", "chalo"}

REJECTIONS = {"no", "n", "nope", "cancel", "stop", "nahi", "na", "mat karo",
              "rehne do", "chhodo"}

AFFIRMATIVE_PREFIXES = ("yes", "ok", "okay", "sure", "haan")

NEGATIVE_PREFIXES = ("no", "cancel", "nahi", "stop")


def is_approval(message: str) -> bool:

    text = (message or "").strip().lower().rstrip("!.")

    if text in APPROVALS:
        return True

    return text.startswith(AFFIRMATIVE_PREFIXES)


def is_rejection(message: str) -> bool:

    text = (message or "").strip().lower().rstrip("!.")

    if text in REJECTIONS:
        return True

    return text.startswith(NEGATIVE_PREFIXES)


class ApprovalStore:

    def __init__(self, ttl=TTL_SECONDS):

        self.ttl = ttl
        self.lock = threading.Lock()
        self.pending = None

    def request(self, tool, arguments, reason=""):

        with self.lock:

            self.pending = {
                "id": uuid.uuid4().hex[:8],
                "tool": tool,
                "arguments": arguments,
                "reason": reason,
                "created": time.time(),
            }

            return dict(self.pending)

    def peek(self):

        with self.lock:

            pending = self.pending

            if not pending:
                return None

            if time.time() - pending["created"] > self.ttl:

                self.pending = None

                return None

            return dict(pending)

    def take(self):

        with self.lock:

            pending = self.pending

            self.pending = None

            if not pending:
                return None

            if time.time() - pending["created"] > self.ttl:
                return None

            return pending

    def clear(self):

        with self.lock:

            self.pending = None


def describe(pending: dict) -> str:

    if not pending:
        return ""

    arguments = pending.get("arguments") or {}

    rendered = ", ".join(
        f"{key}={value!r}" for key, value in arguments.items()
    )

    reason = pending.get("reason") or "This action can change your machine."

    return (
        f"I need your confirmation before I run `{pending['tool']}`"
        f"({rendered}).\n\n{reason}\n\n"
        "Reply **yes** to run it, or **no** to cancel."
    )
