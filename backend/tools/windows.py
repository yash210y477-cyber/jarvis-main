"""Window control on Windows via the Win32 API (ctypes, no extra dependency)."""

import ctypes
from ctypes import wintypes


user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

SW_MINIMIZE = 6
SW_RESTORE = 9

VK_LWIN = 0x5B
KEYEVENTF_KEYUP = 0x0002


def _windows():

    if user32 is None:
        return []

    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def callback(hwnd, _param):

        if not user32.IsWindowVisible(hwnd):
            return True

        length = user32.GetWindowTextLengthW(hwnd)

        if length == 0:
            return True

        buffer = ctypes.create_unicode_buffer(length + 1)

        user32.GetWindowTextW(hwnd, buffer, length + 1)

        title = buffer.value.strip()

        if title:
            found.append({"handle": int(hwnd), "title": title})

        return True

    user32.EnumWindows(callback, 0)

    return found


def list_windows(limit: int = 25) -> dict:

    windows = _windows()

    return {
        "success": True,
        "count": len(windows),
        "windows": windows[:max(1, int(limit))],
    }


def _find(title: str):

    wanted = (title or "").strip().lower()

    if not wanted:
        return None

    windows = _windows()

    for window in windows:

        if window["title"].lower() == wanted:
            return window

    for window in windows:

        if wanted in window["title"].lower():
            return window

    return None


def focus_window(title: str) -> dict:

    if user32 is None:

        return {"success": False, "error": "Window control needs Windows."}

    window = _find(title)

    if not window:

        return {"success": False, "error": f"No open window matches '{title}'."}

    user32.ShowWindow(window["handle"], SW_RESTORE)

    user32.SetForegroundWindow(window["handle"])

    return {"success": True, "window": window["title"]}


def minimize_window(title: str) -> dict:

    if user32 is None:

        return {"success": False, "error": "Window control needs Windows."}

    window = _find(title)

    if not window:

        return {"success": False, "error": f"No open window matches '{title}'."}

    user32.ShowWindow(window["handle"], SW_MINIMIZE)

    return {"success": True, "window": window["title"]}


def minimize_all() -> dict:

    """Show the desktop (Win+D)."""

    if user32 is None:

        return {"success": False, "error": "Window control needs Windows."}

    user32.keybd_event(VK_LWIN, 0, 0, 0)
    user32.keybd_event(ord("D"), 0, 0, 0)
    user32.keybd_event(ord("D"), 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

    return {"success": True, "action": "show_desktop"}
