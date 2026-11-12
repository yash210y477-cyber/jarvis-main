"""Control the browser window: tabs, new window and navigation."""

import ctypes
import time

from tools import windows


user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

SW_RESTORE = 9

VK_CONTROL = 0x11
VK_SHIFT = 0x10
KEYEVENTF_KEYUP = 0x0002

BROWSERS = {
    "chrome": ("google chrome", "chrome"),
    "edge": ("microsoft edge", "edge"),
    "firefox": ("mozilla firefox", "firefox"),
    "brave": ("brave",),
}

DEFAULT_HINTS = (
    "google chrome", "chrome", "microsoft edge", "mozilla firefox", "brave",
)

BROWSER_NAMES = {
    "google chrome": "chrome",
    "chrome": "chrome",
    "microsoft edge": "edge",
    "mozilla firefox": "firefox",
    "brave": "brave",
}

ACTIONS = (
    "new_tab", "new_window", "close_tab", "close_window",
    "reopen_tab", "next_tab", "prev_tab", "switch_tab", "reload",
    "address_bar", "find",
)


def _key(vk, up=False):

    user32.keybd_event(vk, 0, KEYEVENTF_KEYUP if up else 0, 0)


def _combo(vk, shift=False):
    """Press Ctrl (+ Shift) with one key."""

    _key(VK_CONTROL)

    if shift:
        _key(VK_SHIFT)

    time.sleep(0.03)

    _key(vk)
    _key(vk, up=True)

    time.sleep(0.03)

    if shift:
        _key(VK_SHIFT, up=True)

    _key(VK_CONTROL, up=True)


def _focus(browser=""):
    """Bring the browser window forward so shortcuts reach it."""

    hints = BROWSERS.get((browser or "").strip().lower(), DEFAULT_HINTS)

    window = windows.find_matching(hints)

    if not window:
        return None

    user32.ShowWindow(window["handle"], SW_RESTORE)
    user32.SetForegroundWindow(window["handle"])

    time.sleep(0.25)

    return window


def _browser_name(title: str) -> str:

    lowered = (title or "").lower()

    for fragment, name in BROWSER_NAMES.items():

        if fragment in lowered:
            return name

    return "browser"


def control(action, index=None, browser=""):

    if user32 is None:

        return {"success": False, "error": "Browser control needs Windows."}

    action = (action or "").strip().lower().replace(" ", "_")

    aliases = {
        "tab": "new_tab",
        "open_tab": "new_tab",
        "newtab": "new_tab",
        "open_window": "new_window",
        "newwindow": "new_window",
        "close": "close_tab",
        "reopen": "reopen_tab",
        "restore_tab": "reopen_tab",
        "next": "next_tab",
        "previous": "prev_tab",
        "prev": "prev_tab",
        "tab_switch": "switch_tab",
        "jump": "switch_tab",
        "refresh": "reload",
        "url": "address_bar",
        "search": "address_bar",
    }

    action = aliases.get(action, action)

    if action not in ACTIONS:

        return {
            "success": False,
            "error": "Unknown browser action. Use one of: " + ", ".join(ACTIONS),
        }

    window = _focus(browser)

    if window is None:

        return {
            "success": False,
            "error": "No browser window is open right now.",
        }

    name = _browser_name(window["title"])

    if action == "new_tab":

        _combo(0x54)

        message = f"Opened a new tab in {name}."

    elif action == "new_window":

        _combo(0x4E)

        message = f"Opened a new {name} window."

    elif action == "close_tab":

        if index:

            position = max(1, min(9, int(index)))

            _combo(0x30 + position if position < 9 else 0x39)

            time.sleep(0.2)

        _combo(0x57)

        message = (
            f"Closed tab {index} in {name}." if index else f"Closed the tab in {name}."
        )

    elif action == "close_window":

        _combo(0x57, shift=True)

        message = f"Closed the {name} window."

    elif action == "reopen_tab":

        _combo(0x54, shift=True)

        message = f"Reopened the last closed tab in {name}."

    elif action == "next_tab":

        _combo(0x09)

        message = "Switched to the next tab."

    elif action == "prev_tab":

        _combo(0x09, shift=True)

        message = "Switched to the previous tab."

    elif action == "switch_tab":

        position = max(1, min(9, int(index or 1)))

        _combo(0x30 + position if position < 9 else 0x39)

        message = f"Switched to tab {position} in {name}."

    elif action == "reload":

        _combo(0x52)

        message = "Reloaded the page."

    elif action == "address_bar":

        _combo(0x4C)

        message = "Focused the address bar."

    else:

        _combo(0x46)

        message = "Opened find on the page."

    return {
        "success": True,
        "action": action,
        "browser": name,
        "window": window["title"],
        "message": message,
    }
