"""Keyword routing for the tools, so they work without an AI provider.

The agent loop needs a working model. When every provider is down (or no key is
configured) the obvious tool requests still go through here.
"""

import re


MEDIA_WORDS = {
    "play": "play_pause",
    "resume": "play_pause",
    "pause": "play_pause",
    "next track": "next",
    "next song": "next",
    "skip": "next",
    "previous track": "previous",
    "previous song": "previous",
    "mute": "mute",
    "unmute": "mute",
    "volume up": "volume_up",
    "louder": "volume_up",
    "increase volume": "volume_up",
    "volume down": "volume_down",
    "quieter": "volume_down",
    "decrease volume": "volume_down",
    "stop music": "stop",
    "stop playback": "stop",
}

SCREEN_WORDS = (
    "screenshot", "screen shot", "screengrab", "capture screen",
    "screen capture", "screenshot lo",
)

NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
}


def _number(text: str):

    match = re.search(r"(\d+)", text)

    if match:
        return int(match.group(1))

    for word, value in NUMBER_WORDS.items():

        if re.search(rf"\b{word}\b", text):
            return value

    return None


def _timer_seconds(text: str):

    amount = _number(text)

    if amount is None:
        return None

    if re.search(r"\b(hour|hours|ghanta|ghante)\b", text):
        return amount * 3600

    if re.search(r"\b(minute|minutes|min|mins|minute|mint)\b", text):
        return amount * 60

    if re.search(r"\b(second|seconds|sec|secs)\b", text):
        return amount

    # "timer for 5" and "remind me in 10" default to minutes
    return amount * 60


def detect(message: str):

    text = (message or "").strip().lower()

    if not text:
        return None

    # -----------------------------
    # Screenshot
    # -----------------------------

    if any(word in text for word in SCREEN_WORDS):

        return {"tool": "screenshot", "arguments": {"label": "asked"}}

    # -----------------------------
    # Clipboard
    # -----------------------------

    if "clipboard" in text:

        if any(word in text for word in ("copy", "set", "put", "daal", "likh")):
            content = _after(text, ("copy", "clipboard pe", "clipboard par"))
            return {"tool": "set_clipboard", "arguments": {"text": content}}

        return {"tool": "get_clipboard", "arguments": {}}

    # -----------------------------
    # Reminders / alarms
    # -----------------------------

    if re.search(r"\b(remind me|reminder|yaad dilana|yaad rakhna)\b", text):

        match = re.match(
            r"remind me\s+(?:to\s+)?(.+?)(?:\s+(?:at|in|after)\s+(.+))?$",
            text,
        )

        if match:

            body = (match.group(1) or "reminder").strip(" .")
            when = (match.group(2) or "").strip(" .")

            return {
                "tool": "set_reminder",
                "arguments": {
                    "text": body or "reminder",
                    "when": when or "in 10 minutes",
                },
            }

    if re.search(r"\b(alarm|alarms|alarma)\b", text):

        clock_at = re.search(r"(\d{1,2}(?::\d{2})?\s*(?:am|pm|baje))", text)

        if clock_at:

            return {
                "tool": "set_reminder",
                "arguments": {"text": "alarm", "when": clock_at.group(1)},
            }

        seconds = _timer_seconds(text)

        if seconds:

            return {
                "tool": "set_reminder",
                "arguments": {
                    "text": "alarm",
                    "when": f"in {max(1, seconds // 60)} minutes",
                },
            }

        return {"tool": "open_special", "arguments": {"app": "alarm"}}

    # -----------------------------
    # Timers
    # -----------------------------

    if any(word in text for word in ("timer", "alarm", "remind me", "reminder")):

        seconds = _timer_seconds(text)

        if seconds:

            label = _after(text, ("for", "in")).strip(" .!") or "timer"

            return {
                "tool": "set_timer",
                "arguments": {"seconds": seconds, "label": label[:60]},
            }

        if any(word in text for word in ("list", "which", "kitne", "show")):
            return {"tool": "list_timers", "arguments": {}}

        if any(word in text for word in ("cancel", "stop", "hatao", "band")):
            return {"tool": "cancel_timer", "arguments": {}}

    # -----------------------------
    # Windows
    # -----------------------------

    if "show desktop" in text or "desktop dikhao" in text:
        return {"tool": "minimize_all", "arguments": {}}

    if text.startswith("minimize ") and len(text) > 9:
        return {
            "tool": "minimize_window",
            "arguments": {"title": message.strip()[9:].strip()},
        }

    if text.startswith(("focus ", "switch to ")):
        target = text.split(" ", 2)[-1] if text.startswith("switch") else text[6:]
        return {
            "tool": "focus_window",
            "arguments": {"title": target.strip()},
        }

    if "windows" in text and any(word in text for word in ("list", "open", "kaunse")):
        return {"tool": "list_windows", "arguments": {}}

    # -----------------------------
    # Media
    # -----------------------------

    for phrase, action in MEDIA_WORDS.items():

        if re.search(rf"\b{re.escape(phrase)}\b", text):

            if phrase in ("play", "resume") and len(text.split()) > 3:
                # "play despacito" means open music, not toggle transport
                continue

            steps = 1

            if action in ("volume_up", "volume_down"):

                steps = _number(text) or 1

            return {
                "tool": "media_control",
                "arguments": {"action": action, "steps": steps},
            }

    # -----------------------------
    # Files
    # -----------------------------

    match = re.match(r"(?:list|show) files? (?:in )?(.+)", text)

    if match:
        return {"tool": "list_files", "arguments": {"path": match.group(1).strip(" .")}}

    match = re.match(r"read (?:file )?(.+)", text)

    if match:
        return {"tool": "read_file", "arguments": {"path": match.group(1).strip(" .")}}

    # -----------------------------
    # Open folders / files
    # -----------------------------

    match = re.match(
        r"(?:open|kholo|khol)\s+(?:the\s+)?(.+?)(?:\s+(?:folder|directory))?$",
        text,
    )

    if match:

        target = match.group(1).strip(" .")

        if _looks_like_path(target):

            return {"tool": "open_path", "arguments": {"path": target}}

    # -----------------------------
    # Shell (always needs confirmation)
    # -----------------------------

    match = re.match(r"(?:run|execute) (?:the )?(?:command )?(.+)", text)

    if match:
        return {"tool": "run_command", "arguments": {"command": match.group(1).strip()}}

    return None


def _after(text: str, markers):

    for marker in markers:

        if marker in text:

            return text.split(marker, 1)[1].strip(" :")

    return ""


def render(name: str, result: dict) -> str:

    if not result.get("success"):

        return f"That didn't work: {result.get('error') or 'unknown error'}."

    data = result.get("result") if isinstance(result.get("result"), dict) else result

    if name == "screenshot":

        return f"Screenshot saved to `{data.get('path')}`."

    if name == "get_clipboard":

        content = (data.get("content") or "").strip()

        return f"Your clipboard has: {content}" if content else "Your clipboard is empty."

    if name == "set_clipboard":

        return "Copied to your clipboard."

    if name == "media_control":

        return data.get("message") or "Done."

    if name == "list_windows":

        titles = [item["title"] for item in data.get("windows", [])][:10]

        return "Open windows:\n- " + "\n- ".join(titles) if titles else "No windows open."

    if name == "focus_window":

        return f"Focused **{data.get('window')}**."

    if name == "minimize_window":

        return f"Minimized **{data.get('window')}**."

    if name == "minimize_all":

        return "Showing the desktop."

    if name == "list_files":

        entries = data.get("files", [])

        if not entries:
            return f"`{data.get('path')}` is empty."

        lines = [
            f"- {item['name']}{'/' if item['type'] == 'dir' else ''}"
            for item in entries[:30]
        ]

        more = "\n..." if data.get("truncated") else ""

        return f"Contents of `{data.get('path')}`:\n" + "\n".join(lines) + more

    if name == "read_file":

        return f"`{data.get('path')}`:\n\n```\n{data.get('content', '')[:1500]}\n```"

    if name == "set_timer":

        return data.get("message") or "Timer set."

    if name == "list_timers":

        timers = data.get("timers", [])

        if not timers:
            return "No timers running."

        return "Running timers:\n" + "\n".join(
            f"- {item['label']}: {item['remaining']}s left" for item in timers
        )

    if name == "cancel_timer":

        return data.get("message") or "Timer cancelled."

    if name == "run_command":

        output = (data.get("stdout") or data.get("stderr") or "").strip()

        return f"`{data.get('command')}` exited with {data.get('exit_code')}.\n\n```\n{output[:1200]}\n```"

    if name == "get_datetime":

        return data.get("spoken") or str(data)

    if name == "open_path":

        return data.get("message") or f"Opened `{data.get('path')}`."

    if name == "open_special":

        return data.get("message") or "Opened."

    if name == "set_reminder":

        return data.get("message") or "Reminder set."

    if name == "list_reminders":

        items = data.get("reminders", [])

        if not items:
            return "No reminders set."

        return "Reminders:\n" + "\n".join(
            f"- {item['text']} in {max(1, item['remaining'] // 60)} min"
            for item in items
        )

    if name == "cancel_reminder":

        return data.get("message") or "Reminder cancelled."

    if name == "notify":

        return (
            "Notification sent."
            if data.get("success")
            else f"Notification failed: {data.get('error')}"
        )

    return str(data)


PATH_HINTS = (
    "folder", "directory", "downloads", "desktop", "documents",
    "pictures", "photos", "music", "videos", "workspace", "project",
)


def _looks_like_path(target: str) -> bool:

    lowered = (target or "").lower()

    if any(word in lowered for word in PATH_HINTS):

        return True

    if re.search(r"[a-z]:\\", lowered) or "/" in lowered or "\\" in lowered:

        return True

    return bool(re.search(r"\.\w{1,5}$", lowered)) or lowered.startswith("~")
