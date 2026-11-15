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


# What each guarded tool would actually do, said plainly.
PERMISSIONS = {
    "screenshot": (
        "Screen access",
        "I'll capture your whole screen to an image file on this PC.",
    ),
    "read_screen": (
        "Screen access",
        "I'll look at your screen and describe what is open.",
    ),
    "ask_area": (
        "Screen access",
        "I'll capture the part of the screen you drag a box around.",
    ),
    "screen_task": (
        "Screen control",
        "I'll take control of your screen: point, click and type to finish the task.",
    ),
    "screen_watch_start": (
        "Screen access",
        "I'll keep watching your screen in the background and comment on it.",
    ),
    "companion_start": (
        "Microphone + screen",
        "Push-to-talk will listen to you and read the screen when you ask about an area.",
    ),
    "write_file": ("File write", "I'll write a file on this PC."),
    "run_command": ("Command", "I'll run a command on this PC."),
    "close_all_windows": ("Windows", "I'll close every open window."),
    "power_action": ("Power", "I'll change the power state of this PC."),
}

ASK_WORDS = {
    "english": {
        "head": "Permission needed",
        "yes": "Only if you say yes; if you say no, nothing happens.",
    },
    "hinglish": {
        "head": "Permission chahiye",
        "yes": "Sirf tab hoga jab aap haan bolo — na bolo to kuch nahi hoga.",
    },
}


def describe(pending: dict, message: str = "") -> str:
    """A clear permission prompt, not a tool dump."""

    if not pending:
        return ""

    from brain.language import reply_language

    words = ASK_WORDS[
        "hinglish" if reply_language(message or "") == "hinglish" else "english"
    ]

    tool = pending.get("tool", "")
    title, what = PERMISSIONS.get(
        tool, ("Permission needed", "I'll run a tool that changes things on this PC.")
    )

    # A placeholder label says nothing to the user.
    arguments = {
        key: value
        for key, value in (pending.get("arguments") or {}).items()
        if not (key == "label" and str(value).strip().lower() in {"", "asked"})
    }

    details = ", ".join(
        f"{key}={str(value)[:80]!r}" for key, value in arguments.items()
    )

    lines = [f"🔐 {words['head']} — {title}", what]

    if details:

        lines.append(f"Details: {details}")

    lines.append(words["yes"])

    # The chat draws Allow / Cancel buttons for this marker.
    lines.append("[ask]")

    return "\n".join(lines)
