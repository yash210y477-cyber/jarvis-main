"""Open and close desktop apps, restoring a minimized window when possible."""

from tools import windows
from tools.launcher import WindowsLauncher


launcher = WindowsLauncher()


def open_app(app_name: str):

    success, message = launcher.open(app_name)

    return {
        "success": success,
        "action": "open_app",
        "target": app_name,
        "message": message,
    }


def close_app(app_name: str):

    success, message = launcher.close(app_name)

    return {
        "success": success,
        "action": "close_app",
        "target": app_name,
        "message": message,
    }


def close_all_apps():

    return windows.close_all_windows()


def minimize_all_windows():

    return windows.minimize_all()
