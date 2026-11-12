"""Window control on Windows via the Win32 API (ctypes, no extra dependency)."""

import ctypes
import os
from ctypes import wintypes


user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None
kernel32 = ctypes.windll.kernel32 if hasattr(ctypes, "windll") else None

SW_MINIMIZE = 6
SW_RESTORE = 9

WM_CLOSE = 0x0010

VK_LWIN = 0x5B
KEYEVENTF_KEYUP = 0x0002

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


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


def find_matching(names):

    wanted = [name.lower() for name in names if name]

    if not wanted:
        return None

    for window in _windows():

        title = window["title"].lower()

        if any(name in title for name in wanted):
            return window

    return None


def restore_matching(names) -> dict:

    if user32 is None:

        return {"success": False, "error": "Window control needs Windows."}

    window = find_matching(names)

    if not window:

        return {"success": False, "error": "No matching window."}

    user32.ShowWindow(window["handle"], SW_RESTORE)

    user32.SetForegroundWindow(window["handle"])

    return {"success": True, "window": window["title"]}


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


def _own_window_titles():

    """Windows that belong to JARVIS itself must never be closed or hidden."""

    return ("jarvis", "uvicorn", "command prompt", "windows powershell")


def _is_own_process(hwnd) -> bool:

    if kernel32 is None:

        return False

    pid = wintypes.DWORD()

    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    if pid.value in (os.getpid(), os.getppid()):

        return True

    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)

    if not handle:

        return False

    try:

        size = wintypes.DWORD(260)

        buffer = ctypes.create_unicode_buffer(size.value)

        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):

            name = os.path.basename(buffer.value).lower()

            return name in ("python.exe", "pythonw.exe")

    finally:

        kernel32.CloseHandle(handle)

    return False


def minimize_all() -> dict:

    """Minimize every open window at once."""

    if user32 is None:

        return {"success": False, "error": "Window control needs Windows."}

    hidden = []

    for window in _windows():

        if window["title"].lower() in _own_window_titles():
            continue

        if _is_own_process(window["handle"]):
            continue

        user32.ShowWindow(window["handle"], SW_MINIMIZE)

        hidden.append(window["title"])

    return {
        "success": True,
        "action": "minimize_all",
        "count": len(hidden),
        "windows": hidden[:20],
    }


def close_all_windows() -> dict:

    """Ask every open window to close (unsaved work will prompt)."""

    if user32 is None:

        return {"success": False, "error": "Window control needs Windows."}

    closed = []

    for window in _windows():

        if window["title"].lower() in _own_window_titles():
            continue

        if _is_own_process(window["handle"]):
            continue

        user32.PostMessageW(window["handle"], WM_CLOSE, 0, 0)

        closed.append(window["title"])

    return {
        "success": True,
        "action": "close_all",
        "count": len(closed),
        "windows": closed[:20],
        "message": f"Closing {len(closed)} window(s).",
    }
