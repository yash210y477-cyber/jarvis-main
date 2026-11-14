"""Keyword routing for the tools, so they work without an AI provider.

The agent loop needs a working model. When every provider is down (or no key is
configured) the obvious tool requests still go through here.
"""

import re

from tools import browser


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

# Reading the screen needs a vision model, so it is matched before the
# "screenshot" rule, which only saves a file.
WATCH_STOP_PHRASES = (
    "stop watching", "stop the screen watch", "watching band", "screen watch band",
    "screen watching band", "screen dekhna band", "screen dekhna rok",
    "watch band karo", "screen watch stop",
)

WATCH_STATUS_PHRASES = (
    "screen watch status", "is screen watch on", "watching on hai",
    "kya screen watch chal", "screen watching status",
)

WATCH_START_PHRASES = (
    "watch my screen", "watch the screen", "screen watch start",
    "start screen watch", "screen watching start", "screen dekhte raho",
    "screen dekhna shuru", "screen par nazar", "nazar rakho screen",
    "keep watching my screen", "watch screen",
)

REVERSE_PHRASES = (
    "reverse engineer", "reverse-engineer", "reverse eng", "re engineer",
    "reverse engineering", "reverse karo", "reverse kro", "code nikalo",
)

REVERSE_TARGET = re.compile(r"((?:https?://)?[\w-]+(?:\.[\w-]+)+\S*)")

SCREEN_AGENT_PHRASES = (
    "screen agent", "use the screen", "control my screen", "screen pe karo",
    "screen par karo", "screen pe click", "screen par click", "click on ",
    "click the ", "click karo", "button dabao", "button pe click",
    "type this on", "yeh type karo", "type karo", "fill the form",
    "form bharo", "form bhar do", "login karo", "log in karo",
    "sign in karo", "search karo screen", "screen pe search",
    "yeh page pe karo", "is page pe karo", "kar ke dikhao",
)

AREA_PHRASES = (
    "area samjhao", "area samjha", "is area", "yeh area", "ye area",
    "this area", "select area", "screen ka hissa", "screen ka part",
    "part samjhao", "hissa samjhao", "area explain", "explain this part",
    "is part ko", "yeh part", "drag area", "area select karo",
)

GUIDED_PHRASES = (
    "dikhao kaise", "dikha do kaise", "sikhao kaise", "show me how",
    "kaise karte hain", "kaise karna hai", "kaise karu", "kaise karun",
    "mujhe dikhao", "steps dikhao", "walkthrough",
)

SCREEN_READ_PHRASES = (
    "read my screen", "read the screen", "read screen", "look at my screen",
    "look at the screen", "what is on my screen", "whats on my screen",
    "screen dekho", "screen dekh", "screen padho", "screen padh",
    "screen samjhao", "screen samjha", "screen read karo", "screen par kya",
    "summarize this page", "summarise this page", "summarize the page",
    "summarise the page", "summarize page", "page summarize", "page summary",
    "summarize this website", "summarise this website", "summarize this article",
    "this page kya", "yeh page", "ye page", "is page", "iss page", "es page",
    "page ko samjhao", "page padho", "page padh", "page samjhao",
    "explain this page", "what is this page", "what is this website",
    "read this page", "read this website", "website samjhao", "page ka summary",
    "summary do", "summary batao", "screen se batao",
)

SCREEN_WORDS = (
    "screenshot", "screen shot", "screengrab", "capture screen",
    "screen capture", "screenshot lo",
)

SPECIAL_APP_WORDS = (
    "settings", "camera", "photos", "store", "calculator",
    "alarm", "clock", "stopwatch",
)

WEBSITE_PATTERN = re.compile(
    r"^(?:https?://)?[\w-]+(?:\.[\w-]+)*\."
    r"(?:com|in|org|net|io|dev|co|ai|me|app)(?:/\S*)?$"
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


OPEN_VERBS = {
    "open", "launch", "start", "run", "kholo", "khol", "khulo",
    "chalu", "chalao", "chala",
}

CLOSE_VERBS = {"close", "quit", "exit", "kill", "band", "hata", "hatao"}

# These also start shell commands ("run git status"), so they only count
# when the rest of the sentence names an app the launcher knows.
AMBIGUOUS_VERBS = {"run", "start", "chala", "chalao", "chalu"}

# Words that carry no app name, so any word order still works.
FILLER_WORDS = {
    "jarvis", "please", "pls", "zara", "abhi", "bhai", "yaar", "na",
    "kar", "karo", "kro", "krdo", "do", "de", "dijiye", "mera",
    "mujhe", "the", "a", "an", "app", "application", "program",
    "programme", "for", "me", "now", "can", "could", "would",
    "you", "plz", "hey", "ok", "okay",
}


def _app_candidates():
    """Names the launcher already knows; used for typo matching."""

    try:

        from tools import launcher

        return set(launcher.ALIASES) | set(launcher.KNOWN_PATHS)

    except Exception:

        return set()


def _canonical_app(target: str):
    """Map a loosely spoken name onto the name the launcher expects."""

    target = target.strip(" .")

    if not target:

        return ""

    try:

        from tools import launcher

        if target in launcher.ALIASES:

            return launcher.ALIASES[target]

    except Exception:

        pass

    import difflib

    candidates = _app_candidates()

    if target in candidates:

        return target

    close = difflib.get_close_matches(target, sorted(candidates), n=1, cutoff=0.78)

    return close[0] if close else target


def app_action(text: str):
    """(action, app) from any word order: "spotify open", "kholo chrome"."""

    words = re.findall(r"[a-z0-9+.#&'-]+", text)

    if not words:

        return None, ""

    wants_open = any(word in OPEN_VERBS for word in words)
    wants_close = any(word in CLOSE_VERBS for word in words)

    if wants_open == wants_close:

        return None, ""

    skip = OPEN_VERBS | CLOSE_VERBS | FILLER_WORDS

    target_words = [word for word in words if word not in skip]

    if not target_words:

        return None, ""

    spoken = " ".join(target_words)

    # Folders and paths belong to open_path, not to an app launch.
    if any(word in text for word in ("folder", "directory")):

        return None, ""

    if _looks_like_path(spoken):

        return None, ""

    action = "open" if wants_open else "close"

    if {word for word in words if word in OPEN_VERBS | CLOSE_VERBS} <= AMBIGUOUS_VERBS:

        # "run git status" must stay a shell command.
        known = _canonical_app(spoken)

        if known == spoken and spoken not in _app_candidates():

            return None, ""

        return action, known

    return action, _canonical_app(spoken)


def detect(message: str):

    text = (message or "").strip().lower()

    if not text:
        return None

    # -----------------------------
    # Reminders (checked before timers)
    # -----------------------------

    if "reminder" in text and any(
        word in text for word in ("list", "show", "which", "kitne", "what")
    ):

        return {"tool": "list_reminders", "arguments": {}}

    if "reminder" in text and any(
        word in text for word in ("cancel", "delete", "remove", "clear", "hatao")
    ):

        return {"tool": "cancel_reminder", "arguments": {}}

    # -----------------------------
    # Screen watching (background vision)
    # -----------------------------

    if any(phrase in text for phrase in WATCH_STOP_PHRASES):

        return {"tool": "screen_watch_stop", "arguments": {}}

    if any(phrase in text for phrase in WATCH_STATUS_PHRASES):

        return {"tool": "screen_watch_status", "arguments": {}}

    if any(phrase in text for phrase in WATCH_START_PHRASES):

        return {"tool": "screen_watch_start", "arguments": {}}

    # -----------------------------
    # Reverse engineering (REA)
    # -----------------------------

    if any(phrase in text for phrase in REVERSE_PHRASES):

        match = REVERSE_TARGET.search(message.strip())

        if match:

            return {
                "tool": "reverse_engineer",
                "arguments": {"target": match.group(1).strip(" .,")},
            }

    # -----------------------------
    # Screen agent (acts on the screen)
    # -----------------------------

    if any(phrase in text for phrase in AREA_PHRASES):

        return {"tool": "ask_area", "arguments": {"question": message.strip()}}

    # Dictation is checked before the screen agent so "type hello" types
    # instead of being read as a screen task; "type this on the page" still
    # falls through to the agent below.
    early_typed = _typed_text(message)

    if early_typed:

        return {"tool": "type_here", "arguments": {"text": early_typed}}

    if any(phrase in text for phrase in GUIDED_PHRASES):

        return {
            "tool": "screen_task",
            "arguments": {"goal": message.strip(), "guided": True},
        }

    if any(phrase in text for phrase in SCREEN_AGENT_PHRASES):

        return {
            "tool": "screen_task",
            "arguments": {"goal": message.strip()},
        }

    # -----------------------------
    # Typing (dictation into the focused window)
    # -----------------------------

    typed = _typed_text(message)

    if typed:

        return {"tool": "type_here", "arguments": {"text": typed}}

    # -----------------------------
    # Screen reading (vision model)
    # -----------------------------

    if any(phrase in text for phrase in SCREEN_READ_PHRASES):

        return {
            "tool": "read_screen",
            "arguments": {"question": message.strip()},
        }

    # -----------------------------
    # Screenshot
    # -----------------------------

    if any(word in text for word in SCREEN_WORDS):

        return {"tool": "screenshot", "arguments": {"label": "asked"}}

    # -----------------------------
    # Clipboard
    # -----------------------------

    if "clipboard" in text or re.match(r"^(?:please\s+)?copy\s+\S", text):

        wants_write = "clipboard" not in text or any(
            word in text for word in ("copy", "set", "put", "daal", "likh")
        )

        if wants_write:

            content = _clipboard_content(text)

            if content:

                return {"tool": "set_clipboard", "arguments": {"text": content}}

        return {"tool": "get_clipboard", "arguments": {}}

    # -----------------------------
    # Volume: exact level
    # -----------------------------

    if not any(word in text for word in ("mute", "unmute")):

        volume_target = re.search(
            r"(?:volume|awaaz|awaz|sound)\D{0,25}?(\d{1,3})\s*%?",
            text,
        )

        if volume_target:

            percent = max(0, min(100, int(volume_target.group(1))))

            return {"tool": "set_volume", "arguments": {"percent": percent}}

    if re.search(r"\b(volume|awaaz|awaz|sound)\b", text):

        if any(word in text for word in ("kam", "ghata", "decrease", "down")):

            return {
                "tool": "media_control",
                "arguments": {"action": "volume_down", "steps": _number(text) or 1},
            }

        if any(
            word in text
            for word in ("badha", "badhao", "zada", "zyada", "tez", "increase", "up")
        ):

            return {
                "tool": "media_control",
                "arguments": {"action": "volume_up", "steps": _number(text) or 1},
            }

    if text.strip() in (
        "what is the volume", "volume kitna hai", "current volume",
        "how loud is it", "volume level",
    ):

        return {"tool": "get_volume", "arguments": {}}

    # -----------------------------
    # Browser tabs and windows
    # -----------------------------

    if "tab" in text and "window" not in text:

        if any(word in text for word in ("reopen", "restore", "wapas kholo")):
            return {"tool": "browser_control", "arguments": {"action": "reopen_tab"}}

        close_words = ("close", "band", "hatao")

        if any(word in text for word in close_words):

            match = re.search(
                r"(\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|"
                r"seventh|eighth|ninth|last)\s+tab",
                text,
            )

            if match:
                return {
                    "tool": "browser_control",
                    "arguments": {
                        "action": "close_tab",
                        "index": _tab_index(match.group(1)),
                    },
                }

            return {"tool": "browser_control", "arguments": {"action": "close_tab"}}

        position = re.search(
            r"(\d+(?:st|nd|rd|th)|first|second|third|fourth|fifth|sixth|"
            r"seventh|eighth|ninth|last)\s+tab",
            text,
        )

        if position and any(
            word in text
            for word in ("open", "go", "jump", "switch", "show", "jao", "par")
        ):

            return {
                "tool": "browser_control",
                "arguments": {
                    "action": "switch_tab",
                    "index": _tab_index(position.group(1)),
                },
            }

        if any(word in text for word in ("next", "agli", "agla")):
            return {"tool": "browser_control", "arguments": {"action": "next_tab"}}

        if any(word in text for word in ("previous", "prev", "pichhli", "pichla")):
            return {"tool": "browser_control", "arguments": {"action": "prev_tab"}}

        if any(word in text for word in ("new tab", "naya tab", "nayi tab")):
            return {"tool": "browser_control", "arguments": {"action": "new_tab"}}

    if any(
        phrase in text
        for phrase in ("close this window", "close the window", "close new window")
    ):
        return {"tool": "browser_control", "arguments": {"action": "close_window"}}

    if "new tab" in text or "naya tab" in text or "nayi tab" in text:
        return {"tool": "browser_control", "arguments": {"action": "new_tab"}}

    if "new window" in text or "naya window" in text or "nayi window" in text:
        return {"tool": "browser_control", "arguments": {"action": "new_window"}}

    if "tab" in text and "window" not in text:
        return {"tool": "browser_control", "arguments": {"action": "new_tab"}}

    # -----------------------------
    # Websites: search on a site, visit a site
    # -----------------------------

    match = re.search(
        r"search\s+(?:for\s+)?(.+?)\s+(?:in|on)\s+"
        r"(youtube|google|github|wikipedia|amazon|flipkart|spotify)\s*$",
        text,
    )

    if match:

        return {
            "tool": "search_site",
            "arguments": {
                "query": match.group(1).strip(),
                "site": match.group(2),
            },
        }

    match = re.search(
        r"(?:visit|go to|open site)\s+(?:the\s+)?(.+?)(?:\s+(?:website|site))?$",
        text,
    )

    if match:

        target = match.group(1).strip(" .")

        if target and browser.site_url(target):

            return {"tool": "open_site", "arguments": {"name": target}}

    match = re.match(r"search\s+(?:for\s+)?(.+)$", text)

    if match:

        return {
            "tool": "search_site",
            "arguments": {"query": match.group(1).strip(), "site": "google"},
        }

    # -----------------------------
    # Reminders / alarms
    # -----------------------------

    if re.search(r"\breminders?\b", text) and any(
        word in text for word in ("list", "show", "which", "kitne", "what")
    ):

        return {"tool": "list_reminders", "arguments": {}}

    if re.search(r"\breminders?\b", text) and any(
        word in text for word in ("cancel", "delete", "remove", "clear", "hatao")
    ):

        return {"tool": "cancel_reminder", "arguments": {}}

    if re.search(r"\b(remind me|reminder|yaad dilana|yaad rakhna)\b", text):

        match = re.match(
            r"remind me\s+(?:to\s+)?(.+?)(?:\s+(?:at|in|after)\s+(.+))?$",
            text,
        )

        if match:

            body = (match.group(1) or "reminder").strip(" .")
            when = (match.group(2) or "").strip(" .")

            # "2 minutes" without a leading "in" must stay relative
            if when and re.match(
                r"^\d+(\.\d+)?\s*(second|seconds|sec|secs|minute|minutes|min|mins|hour|hours|hr|hrs)\s*$",
                when,
            ):
                when = "in " + when

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

    if any(
        phrase in text
        for phrase in ("show desktop", "desktop dikhao", "hide all windows")
    ):
        return {"tool": "minimize_all", "arguments": {}}

    if ("minimize" in text or "minimise" in text) and any(
        word in text
        for word in ("all", "everything", "sab", "saare", "saari", "sare")
    ):
        return {"tool": "minimize_all", "arguments": {}}

    if ("close" in text or "band" in text) and any(
        word in text
        for word in ("all", "everything", "sab", "saare", "saari", "sare")
    ):
        return {"tool": "close_all_windows", "arguments": {}}

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
    # Lock / power
    # -----------------------------

    if "lock" in text and "screen" in text:
        return {"tool": "lock_screen", "arguments": {}}

    if "lock" in text and ("pc" in text or "laptop" in text):
        return {"tool": "lock_screen", "arguments": {}}

    if "shutdown" in text or "shut down" in text or "power off" in text:
        return {"tool": "power_action", "arguments": {"action": "shutdown"}}
    if "restart" in text or "reboot" in text:
        return {"tool": "power_action", "arguments": {"action": "restart"}}
    if "sleep" in text or "suspend" in text:
        return {"tool": "power_action", "arguments": {"action": "sleep"}}
    if "sign out" in text or "log out" in text:
        return {"tool": "power_action", "arguments": {"action": "signout"}}
    if "lock" in text:
        return {"tool": "power_action", "arguments": {"action": "lock"}}

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
    # Close one app
    # -----------------------------

    match = re.match(
        r"(?:close|quit|exit|kill|band karo)\s+(?:the\s+)?(.+?)(?:\s+app)?$",
        text,
    )

    if match:

        target = match.group(1).strip(" .")

        if target:
            return {"tool": "close_app", "arguments": {"app_name": target}}

    # -----------------------------
    # Open folders / files
    # -----------------------------

    match = re.match(
        r"(?:open|kholo|khol)\s+(?:the\s+)?(.+?)(?:\s+(?:folder|directory))?$",
        text,
    )

    if match:

        target = match.group(1).strip(" .")

        if target and WEBSITE_PATTERN.match(target):

            return {"tool": "open_website", "arguments": {"url": target}}

        # "kholo" is a verb, not a folder hint: "kholo spotify" is an app.
        folder_words = ("folder", "directory", "drive")

        if _looks_like_path(target) or any(word in text for word in folder_words):

            return {"tool": "open_path", "arguments": {"path": target}}

    match = re.match(
        r"(?:open|launch|start|kholo|khol)\s+(?:the\s+)?(.+?)(?:\s+app)?$",
        text,
    )

    if match:

        target = match.group(1).strip(" .")

        if target and WEBSITE_PATTERN.match(target):
            return {"tool": "open_website", "arguments": {"url": target}}

        if target in SPECIAL_APP_WORDS or target in (
            "windows settings", "pc settings", "system settings",
        ):
            return {
                "tool": "open_special",
                "arguments": {
                    "app": "settings" if "settings" in target else target,
                },
            }

        if target:
            return {"tool": "open_app", "arguments": {"app_name": target}}

    # -----------------------------
    # Any word order, e.g. "spotify open" or "kholo chrome"
    # -----------------------------

    action, target = app_action(text)

    if action == "open" and target:

        return {"tool": "open_app", "arguments": {"app_name": target}}

    if action == "close" and target:

        return {"tool": "close_app", "arguments": {"app_name": target}}

    # -----------------------------
    # Hinglish word order: "chrome kholo", "notepad band karo"
    # -----------------------------

    match = re.match(
        r"^(?:please\s+)?(.+?)\s+(?:kholo|khol\s+do|khol|chalu\s+karo|"
        r"open\s+karo|open\s+kar\s+do)$",
        text,
    )

    if match:

        target = match.group(1).strip(" .")

        if target and WEBSITE_PATTERN.match(target):

            return {"tool": "open_website", "arguments": {"url": target}}

        # "downloads folder kholo" is a folder, not an app.
        folder = re.sub(r"\s*(?:folder|directory)$", "", target).strip(" .")

        if folder != target or _looks_like_path(target):

            return {"tool": "open_path", "arguments": {"path": folder or target}}

        if target in SPECIAL_APP_WORDS:

            return {"tool": "open_special", "arguments": {"app": target}}

        if target:

            return {"tool": "open_app", "arguments": {"app_name": target}}

    match = re.match(
        r"^(?:please\s+)?(.+?)\s+(?:band\s+karo|band\s+kar\s+do|close\s+karo|"
        r"hata\s+do)$",
        text,
    )

    if match:

        target = match.group(1).strip(" .")

        if target:

            return {"tool": "close_app", "arguments": {"app_name": target}}

    # -----------------------------
    # Shell (always needs confirmation)
    # -----------------------------

    match = re.match(r"(?:run|execute) (?:the )?(?:command )?(.+)", text)

    if match:
        return {"tool": "run_command", "arguments": {"command": match.group(1).strip()}}

    return None


TAB_WORDS = {
    "first": 1, "1st": 1,
    "second": 2, "2nd": 2,
    "third": 3, "3rd": 3,
    "fourth": 4, "4th": 4,
    "fifth": 5, "5th": 5,
    "sixth": 6, "6th": 6,
    "seventh": 7, "7th": 7,
    "eighth": 8, "8th": 8,
    "ninth": 9, "9th": 9,
    "last": 9,
}


def _tab_index(word: str) -> int:

    word = (word or "").strip().lower()

    if word.isdigit():
        return max(1, min(9, int(word)))

    return TAB_WORDS.get(word, 1)


TYPED_PATTERNS = (
    r"^(?:jarvis[,\s]+)?(?:please\s+)?(?:write|type)\s+(.+?)\s+(?:here|yahan)$",
    r"^(?:jarvis[,\s]+)?(?:please\s+)?(?:write|type)\s+(?:here|yahan)\s*[:\-]?\s*(.+)$",
    r"^(?:yahan|here)\s+(?:likho|likh\s+do|type\s+karo)\s*[:\-]?\s*(.+)$",
    r"^(?:yahan|here)\s+(.+?)\s+(?:likho|likh\s+do|type\s+karo)$",
    r"^(.+?)\s+(?:yahan\s+)?(?:likho|likh\s+do|type\s+karo)$",
)


# "type this on the page" is screen work, not dictation.
SCREENISH = (
    "page", "screen", "button", "form", "field", "window", "app", "browser",
    "menu", "link", "icon", "tab", "site", "website", "click", "scroll",
)

# "write a poem" / "write a function" are requests, not dictation.
DICTATION_STOP = (
    "a", "an", "the", "me", "my", "code", "function", "script", "program",
    "email", "letter", "essay", "poem", "story", "python", "paragraph",
)


def _bare_dictation(content: str) -> str:
    """Short \"type hello\" style speech; long or screen-bound text is not."""

    content = content.strip(" \"'.,;:")

    lower = content.lower()

    if not content or "?" in content:

        return ""

    if len(content.split()) > 6:

        return ""

    if lower.split(" ")[0] in DICTATION_STOP:

        return ""

    if re.match(r"^(this|it|that)\b", lower):

        return ""

    if any(word in lower for word in SCREENISH):

        return ""

    return content


def _typed_text(message: str) -> str:
    """What to type, from "type hello" / "write hello here" / "hello likho"."""

    raw = (message or "").strip()

    if not raw:

        return ""

    # "type karo hello", "likho hello" — the verb comes first.
    verb_first = re.match(
        r"^(?:jarvis[,\s]+)?(?:please\s+)?(?:type|write)\s+(?:karo|kar\s+do)\s+(.+)$",
        raw,
        re.IGNORECASE,
    )

    if verb_first:

        return _bare_dictation(verb_first.group(1))

    hinglish_first = re.match(
        r"^(?:jarvis[,\s]+)?(?:please\s+)?(?:likho|likh\s+do)\s+(.+)$",
        raw,
        re.IGNORECASE,
    )

    if hinglish_first:

        return _bare_dictation(hinglish_first.group(1))

    for pattern in TYPED_PATTERNS:

        match = re.match(pattern, raw, re.IGNORECASE)

        if not match:

            continue

        content = match.group(1).strip(" \"'.,;:")

        if not content or re.fullmatch(r"(?:this|it|that)", content, re.IGNORECASE):

            return ""

        return content

    # Finally the plain "type hello" / "write hello" form.
    bare = re.match(
        r"^(?:jarvis[,\s]+)?(?:please\s+)?(?:type|write)\s+(.+)$",
        raw,
        re.IGNORECASE,
    )

    if bare:

        return _bare_dictation(bare.group(1))

    return ""


def _clipboard_content(text: str) -> str:
    """The text to copy, with the clipboard words and the verb taken out."""

    content = text

    # Longest phrases first: "into the clipboard" must not leave a stray "in".
    for phrase in (
        "into the clipboard", "in my clipboard", "on the clipboard",
        "to the clipboard", "to clipboard", "clipboard me", "clipboard pe",
        "clipboard par", "clipboard",
    ):

        content = content.replace(phrase, " ")

    content = re.sub(r"\b(?:please|pls)\b", " ", content)

    content = re.sub(r"^\s*copy\b", " ", content, count=1)

    content = re.sub(r"\s+(?:copy|karo|kar|kro|do)\s*$", " ", content)

    content = re.sub(r"\s+(?:copy|karo|kar|kro|do)\s*$", " ", content)

    content = re.sub(r"\s+to\s*$", " ", content)

    content = re.sub(r"^\s*(?:the\s+)?text\s+", "", content)

    return re.sub(r"\s+", " ", content).strip(" .,")


def _after(text: str, markers):

    for marker in markers:

        if marker in text:

            return text.split(marker, 1)[1].strip(" :")

    return ""


def render(name: str, result: dict, hinglish: bool = False) -> str:

    """Tool result as text, in the language the user asked with."""

    data = result.get("result") if isinstance(result.get("result"), dict) else result

    inner = result.get("result") if isinstance(result.get("result"), dict) else {}

    if not result.get("success") or inner.get("success") is False:

        error = (
            result.get('error') or inner.get('error') or 'unknown error'
        ).strip().rstrip('.')

        if hinglish:

            return f"Ye nahi ho paya: {error}."

        return f"That didn't work: {error}."

    if name == "generate_image":

        if hinglish:

            return f"Image ban gayi: `{data.get('path')}`"

        return f"Here is your image: `{data.get('path')}`"

    if name == "ask_area":

        return data.get("answer") or "Area explained."

    if name in ("companion_start", "companion_stop", "companion_status"):

        if name == "companion_status":

            return (
                f"Push-to-talk: {'on' if data.get('running') else 'off'}, "
                f"orb: {'on' if data.get('orb') else 'off'}."
            )

        return data.get("message") or data.get("error") or "Done."

    if name in ("orb_start", "orb_stop", "show_card"):

        return data.get("message") or "Done."

    if name == "type_here":

        return data.get("message") or "Typed."

    if name in ("screen_watch_start", "screen_watch_stop"):

        return data.get("message") or data.get("error") or "Done."

    if name == "screen_watch_status":

        if not data.get("watching"):

            return "Screen watch band hai. \"watch my screen\" bolo to shuru karu."

        return (
            f"Screen watch chal raha hai ({data.get('frames')} frames, "
            f"{data.get('events')} events)."
        )

    if name == "reverse_engineer":

        return data.get("summary") or "Analysis finished."

    if name == "screen_task":

        from tools import screen_agent

        return screen_agent.narrate(data) or data.get("answer") or "Done."

    if name == "read_screen":

        answer = (data.get("answer") or "").strip()

        return answer or "Screen dekha par kuch samajh nahi aaya."

    if name == "screenshot":

        if hinglish:

            return f"Screenshot `{data.get('path')}` me save ho gaya."

        return f"Screenshot saved to `{data.get('path')}`."

    if name == "get_clipboard":

        content = (data.get("content") or "").strip()

        return f"Your clipboard has: {content}" if content else "Your clipboard is empty."

    if name == "set_clipboard":

        return (
            "Clipboard me copy kar diya."
            if hinglish
            else "Copied to your clipboard."
        )

    if name in (
        "media_control", "set_volume", "get_volume", "browser_control",
        "open_site", "search_site",
    ):

        return data.get("message") or "Done."

    if name == "list_windows":

        titles = [item["title"] for item in data.get("windows", [])][:10]

        return "Open windows:\n- " + "\n- ".join(titles) if titles else "No windows open."

    if name == "focus_window":

        return f"Focused **{data.get('window')}**."

    if name == "minimize_window":

        return f"Minimized **{data.get('window')}**."

    if name == "minimize_all":

        count = data.get("count")

        return f"Minimized {count} window(s)." if count else "Showing the desktop."

    if name in ("open_app", "close_app"):

        return data.get("message") or "Done."

    if name == "close_all_windows":

        return data.get("message") or "Closing the windows."

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
