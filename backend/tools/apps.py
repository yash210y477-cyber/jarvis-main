"""Open and close desktop apps, restoring a minimized window when possible."""

from tools import windows
from tools.launcher import WindowsLauncher


launcher = WindowsLauncher()

# Words that ride along with a spoken app name: "open figma please".
TRAILING_WORDS = {
    "please", "pls", "plz", "now", "for", "me", "the", "a", "an",
    "yaar", "bhai", "zara", "abhi", "na", "app", "application",
    "jarvis", "hey", "ok", "okay", "and", "then", "phir",
    "open", "launch", "start", "kholo", "khol", "close", "band",
    "chalu", "chala", "karo", "kar", "kro", "krdo", "do", "de",
}


def clean_app_name(name: str) -> str:
    """Drop filler words so the launcher only sees the app itself."""

    words = (name or "").split()

    while words and words[0].strip(".,!?").lower() in TRAILING_WORDS:

        words.pop(0)

    while words and words[-1].strip(".,!?").lower() in TRAILING_WORDS:

        words.pop()

    return " ".join(words) or (name or "").strip()


def open_app(app_name: str):

    app_name = clean_app_name(app_name)

    success, message = launcher.open(app_name)

    if not success:

        # Not an installed app: maybe the user meant the website.
        from tools import browser

        if browser.site_url(app_name):

            opened = browser.open_site(app_name)

            return {
                "success": opened.get("success", False),
                "action": "open_site",
                "target": app_name,
                "message": opened.get("message") or f"Opening {app_name}.",
            }

    return {
        "success": success,
        "action": "open_app",
        "target": app_name,
        "message": message,
    }


def close_app(app_name: str):

    app_name = clean_app_name(app_name)

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
