"""The default registry: every tool the agent can call."""

from tools.registry import CONFIRM, ToolRegistry
from tools.executor import ActionExecutor

from tools import (
    clipboard,
    clock,
    desktop,
    files,
    media,
    screenshot,
    shell,
    timer,
    windows,
)


OBJECT = "object"


def _schema(properties, required=None):

    return {
        "type": OBJECT,
        "properties": properties,
        "required": required or [],
    }


def build_registry():

    registry = ToolRegistry()

    # -----------------------------
    # Files (sandboxed)
    # -----------------------------

    registry.register(
        "list_files",
        files.list_files,
        description="List files and folders inside the JARVIS workspace.",
        schema=_schema(
            {
                "path": {
                    "type": "string",
                    "description": "Folder relative to the workspace root.",
                },
                "limit": {"type": "integer", "description": "Max entries."},
            },
        ),
        category="files",
        examples=["list files in backend", "what's in the workspace"],
    )

    registry.register(
        "read_file",
        files.read_file,
        description="Read a UTF-8 text file from inside the workspace.",
        schema=_schema(
            {
                "path": {"type": "string", "description": "File path."},
                "max_chars": {"type": "integer", "description": "Max characters."},
            },
            ["path"],
        ),
        category="files",
        examples=["read backend/main.py"],
    )

    registry.register(
        "write_file",
        files.write_file,
        description="Create or overwrite a text file inside the workspace.",
        schema=_schema(
            {
                "path": {"type": "string", "description": "File path."},
                "content": {"type": "string", "description": "Full file content."},
                "append": {"type": "boolean", "description": "Append instead of overwrite."},
            },
            ["path", "content"],
        ),
        permission=CONFIRM,
        category="files",
        examples=["write notes.txt with my plan"],
    )

    # -----------------------------
    # Shell
    # -----------------------------

    registry.register(
        "run_command",
        shell.run_command,
        description=(
            "Run one allowlisted shell command in the workspace and return its "
            "output. Destructive commands are refused."
        ),
        schema=_schema(
            {
                "command": {"type": "string", "description": "Command to run."},
                "timeout": {"type": "integer", "description": "Seconds, max 30."},
            },
            ["command"],
        ),
        permission=CONFIRM,
        category="shell",
        examples=["run git status", "run python --version"],
    )

    # -----------------------------
    # Clipboard
    # -----------------------------

    registry.register(
        "get_clipboard",
        clipboard.get_clipboard,
        description="Read the current clipboard text.",
        schema=_schema({}),
        category="clipboard",
        examples=["what's in my clipboard"],
    )

    registry.register(
        "set_clipboard",
        clipboard.set_clipboard,
        description="Replace the clipboard contents with text.",
        schema=_schema(
            {"text": {"type": "string", "description": "Text to copy."}},
            ["text"],
        ),
        category="clipboard",
        examples=["copy my email address"],
    )

    # -----------------------------
    # Screen
    # -----------------------------

    registry.register(
        "screenshot",
        screenshot.capture_screen,
        description="Capture the primary screen to a PNG file and return its path.",
        schema=_schema(
            {"label": {"type": "string", "description": "Optional short label."}},
        ),
        category="screen",
        examples=["take a screenshot"],
    )

    # -----------------------------
    # Windows
    # -----------------------------

    registry.register(
        "list_windows",
        windows.list_windows,
        description="List open windows with their titles.",
        schema=_schema({"limit": {"type": "integer"}}),
        category="windows",
        examples=["which windows are open"],
    )

    registry.register(
        "focus_window",
        windows.focus_window,
        description="Bring an open window to the foreground by (partial) title.",
        schema=_schema(
            {"title": {"type": "string", "description": "Window title or part of it."}},
            ["title"],
        ),
        category="windows",
        examples=["focus chrome"],
    )

    registry.register(
        "minimize_window",
        windows.minimize_window,
        description="Minimize an open window by (partial) title.",
        schema=_schema(
            {"title": {"type": "string", "description": "Window title or part of it."}},
            ["title"],
        ),
        category="windows",
        examples=["minimize notepad"],
    )

    registry.register(
        "minimize_all",
        windows.minimize_all,
        description="Minimize every window (show the desktop).",
        schema=_schema({}),
        category="windows",
        examples=["show my desktop"],
    )

    # -----------------------------
    # Media
    # -----------------------------

    registry.register(
        "media_control",
        media.control,
        description="Play/pause, skip tracks, mute or change the volume.",
        schema=_schema(
            {
                "action": {
                    "type": "string",
                    "enum": [
                        "play_pause", "next", "previous", "stop",
                        "mute", "volume_up", "volume_down",
                    ],
                },
                "steps": {
                    "type": "integer",
                    "description": "How many volume steps (default 1).",
                },
            },
            ["action"],
        ),
        category="media",
        examples=["pause the music", "volume up"],
    )

    # -----------------------------
    # Timers
    # -----------------------------

    registry.register(
        "set_timer",
        lambda seconds, label="": timer.TIMERS.set(seconds, label),
        description="Set a timer that beeps when it finishes.",
        schema=_schema(
            {
                "seconds": {"type": "integer", "description": "Duration in seconds."},
                "label": {"type": "string", "description": "What it is for."},
            },
            ["seconds"],
        ),
        category="timer",
        examples=["set a timer for 5 minutes", "remind me in 10 minutes"],
    )

    registry.register(
        "list_timers",
        timer.TIMERS.list,
        description="List the timers that are still running.",
        schema=_schema({}),
        category="timer",
        examples=["which timers are running"],
    )

    registry.register(
        "cancel_timer",
        lambda timer_id="": timer.TIMERS.cancel(timer_id),
        description="Cancel a running timer (the newest one when no id is given).",
        schema=_schema({"timer_id": {"type": "string"}}),
        category="timer",
        examples=["cancel the timer"],
    )

    # -----------------------------
    # Local clock
    # -----------------------------

    registry.register(
        "get_datetime",
        clock.get_datetime,
        description=(
            "Read the machine clock: date, day, month, year, week, "
            "time or timezone. Works offline."
        ),
        schema=_schema(
            {
                "part": {
                    "type": "string",
                    "enum": [
                        "now", "date", "time", "weekday", "day",
                        "month", "year", "week", "timezone", "iso",
                    ],
                }
            },
        ),
        category="clock",
        examples=["what is the current month", "what day is it"],
    )

    # -----------------------------
    # Folders, files and system apps
    # -----------------------------

    registry.register(
        "open_path",
        desktop.open_path,
        description=(
            "Open a folder or file with the default Windows program. "
            "Accepts downloads/desktop/documents and full paths."
        ),
        schema=_schema(
            {"path": {"type": "string", "description": "Folder or file."}},
            ["path"],
        ),
        category="desktop",
        examples=["open downloads folder", "open backend/main.py"],
    )

    registry.register(
        "open_special",
        desktop.open_special,
        description=(
            "Open a built-in Windows app such as alarm, clock, "
            "settings, calculator, camera, photos or store."
        ),
        schema=_schema(
            {"app": {"type": "string", "description": "App name."}},
            ["app"],
        ),
        category="desktop",
        examples=["open the alarm app", "open windows settings"],
    )

    # -----------------------------
    # Reminders + notifications
    # -----------------------------

    def _scheduler():

        from reminders.scheduler import SCHEDULER

        return SCHEDULER

    registry.register(
        "set_reminder",
        lambda text, when="", seconds=None: _scheduler().add(
            text, when, seconds
        ),
        description=(
            "Set a reminder or alarm; it fires a Windows toast. "
            "Use when=\"in 10 minutes\" or when=\"at 7:30 am\"."
        ),
        schema=_schema(
            {
                "text": {"type": "string", "description": "What to remind."},
                "when": {"type": "string", "description": "When it fires."},
                "seconds": {"type": "integer", "description": "Seconds from now."},
            },
            ["text"],
        ),
        category="reminder",
        examples=["remind me to drink water in 20 minutes"],
    )

    registry.register(
        "list_reminders",
        lambda: {"success": True, "reminders": _scheduler().list()},
        description="List the reminders that are still waiting.",
        schema=_schema({}),
        category="reminder",
        examples=["which reminders do I have"],
    )

    registry.register(
        "cancel_reminder",
        lambda reminder_id="": _scheduler().cancel(reminder_id),
        description="Cancel one reminder, or the newest when no id is given.",
        schema=_schema({"reminder_id": {"type": "string"}}),
        category="reminder",
        examples=["cancel my reminder"],
    )

    registry.register(
        "notify",
        lambda title="JARVIS", message="", app="JARVIS": _toast(
            title, message, app
        ),
        description="Show a Windows toast notification.",
        schema=_schema(
            {
                "title": {"type": "string"},
                "message": {"type": "string"},
                "app": {"type": "string"},
            },
            ["message"],
        ),
        category="notification",
        examples=["notify me that the build finished"],
    )

    return registry


REGISTRY = build_registry()

EXECUTOR = ActionExecutor(REGISTRY)


def _toast(title, message, app="JARVIS"):

    from notify.toast import notify

    return notify(title, message, app)
