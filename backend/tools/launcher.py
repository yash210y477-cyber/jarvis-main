"""Find and launch Windows applications, including Store (UWP) apps."""

import json
import os
import shutil
import subprocess
import winreg
from pathlib import Path

from tools import windows


def _env(name, default=""):
    return Path(os.environ.get(name, default))


START_MENU_DIRS = [
    _env("ProgramData", r"C:\ProgramData")
    / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    _env("APPDATA") / "Microsoft" / "Windows" / "Start Menu" / "Programs",
]

PROGRAM_DIRS = [
    _env("ProgramFiles", r"C:\Program Files"),
    _env("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    _env("LOCALAPPDATA"),
    _env("APPDATA"),
    _env("LOCALAPPDATA") / "Programs",
    _env("APPDATA") / "Programs",
]

ALIASES = {
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "terminal": "cmd",
    "command prompt": "cmd",
    "calculator": "calc",
    "file explorer": "explorer",
    "google chrome": "chrome",
}

# Installers that keep their exe somewhere the generic search misses.
KNOWN_PATHS = {
    "whatsapp": [
        _env("LOCALAPPDATA") / "WhatsApp" / "WhatsApp.exe",
        _env("LOCALAPPDATA") / "Programs" / "WhatsApp" / "WhatsApp.exe",
        _env("ProgramFiles") / "WhatsApp" / "WhatsApp.exe",
    ],
    "whatsapp desktop": [
        _env("LOCALAPPDATA") / "WhatsApp" / "WhatsApp.exe",
        _env("LOCALAPPDATA") / "Programs" / "WhatsApp" / "WhatsApp.exe",
    ],
    "telegram": [
        _env("APPDATA") / "Telegram Desktop" / "Telegram.exe",
        _env("LOCALAPPDATA") / "Telegram Desktop" / "Telegram.exe",
        _env("ProgramFiles") / "Telegram Desktop" / "Telegram.exe",
    ],
    "telegram desktop": [
        _env("APPDATA") / "Telegram Desktop" / "Telegram.exe",
        _env("LOCALAPPDATA") / "Telegram Desktop" / "Telegram.exe",
    ],
    "spotify": [
        _env("APPDATA") / "Spotify" / "Spotify.exe",
    ],
}

# Fragments of window titles that mean "this app is already running".
WINDOW_HINTS = {
    "chrome": ("google chrome", "chrome"),
    "google chrome": ("google chrome", "chrome"),
    "edge": ("microsoft edge", "edge"),
    "msedge": ("microsoft edge", "edge"),
    "firefox": ("mozilla firefox", "firefox"),
    "code": ("visual studio code",),
    "whatsapp": ("whatsapp",),
    "telegram": ("telegram",),
    "spotify": ("spotify",),
    "discord": ("discord",),
    "notepad": ("notepad",),
    "explorer": ("file explorer",),
    "word": ("word",),
    "excel": ("excel",),
    "powerpoint": ("powerpoint",),
    "store": ("microsoft store",),
    "calc": ("calculator",),
}

_START_APPS_CACHE = None


def start_apps():
    """Name -> AppID map for everything in the Start menu, Store apps too."""

    global _START_APPS_CACHE

    if _START_APPS_CACHE is not None:
        return _START_APPS_CACHE

    mapping = {}

    try:

        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "Get-StartApps | ConvertTo-Json -Compress",
            ],
            capture_output=True,
            text=True,
            timeout=25,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        if result.returncode == 0 and result.stdout.strip():

            data = json.loads(result.stdout)

            if isinstance(data, dict):
                data = [data]

            for item in data:

                name = (item.get("Name") or "").strip()
                app_id = (item.get("AppID") or "").strip()

                if name and app_id:
                    mapping[name.lower()] = app_id

    except Exception:

        mapping = {}

    _START_APPS_CACHE = mapping

    return mapping


class WindowsLauncher:

    def normalize(self, name: str):

        cleaned = (name or "").strip().strip("\"'")

        for suffix in (" app", " application"):

            if cleaned.lower().endswith(suffix):
                cleaned = cleaned[: -len(suffix)].strip()

        return ALIASES.get(cleaned.lower(), cleaned)

    def window_hints(self, app: str):

        key = self.normalize(app).lower()

        hints = WINDOW_HINTS.get(key)

        return hints or (key,)

    def restore(self, app: str):
        """Bring an already running window back instead of opening a new one."""

        result = windows.restore_matching(self.window_hints(app))

        return result if result.get("success") else None

    def search_path(self, app):

        return shutil.which(app)

    def search_known_paths(self, app):

        for path in KNOWN_PATHS.get(app.lower(), []):

            if path.exists():
                return str(path)

        return None

    def search_registry(self, app):

        roots = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]

        keys = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths",
        ]

        names = [app, app + ".exe"]

        for root in roots:

            for key in keys:

                for exe in names:

                    try:

                        reg = winreg.OpenKey(root, key + "\\" + exe)

                        value, _ = winreg.QueryValueEx(reg, "")

                        if os.path.exists(value):
                            return value

                    except Exception:
                        pass

        return None

    def search_start_menu(self, app):

        target = app.lower()

        for root in START_MENU_DIRS:

            if not root.exists():
                continue

            try:

                for item in root.rglob("*"):

                    if item.suffix.lower() not in (".lnk", ".exe", ".url"):
                        continue

                    if target in item.stem.lower():
                        return str(item)

            except Exception:
                pass

        return None

    def search_program_files(self, app):

        target = app.lower()

        for root in PROGRAM_DIRS:

            if not root.exists():
                continue

            try:

                for exe in root.rglob("*.exe"):

                    name = exe.stem.lower()

                    if target == name or target in name or name in target:
                        return str(exe)

            except Exception:
                pass

        return None

    def find_start_app(self, app):
        """Match a Store / Start-menu app by name and return its AppID."""

        target = app.lower().strip()

        apps = start_apps()

        if not apps:
            return None

        if target in apps:
            return apps[target]

        for name, app_id in apps.items():

            if target in name:
                return app_id

        for name, app_id in apps.items():

            if name in target:
                return app_id

        return None

    def find_application(self, app):

        path = self.search_known_paths(app) or self.search_path(app)

        if path:
            return path

        path = self.search_registry(app)

        if path:
            return path

        path = self.search_start_menu(app)

        if path:
            return path

        app_id = self.find_start_app(app)

        if app_id:
            return "shell:AppsFolder\\" + app_id

        return self.search_program_files(app)

    def open(self, app):

        app = self.normalize(app)

        restored = self.restore(app)

        if restored:
            return True, f"{restored['window']} was minimized, brought it back."

        target = self.find_application(app)

        if target is None:
            return False, f"Application '{app}' not found."

        try:

            if target.startswith("shell:AppsFolder\\"):

                subprocess.Popen(["explorer.exe", target], shell=False)

            elif target.lower().endswith((".lnk", ".url")):

                os.startfile(target)

            elif target.lower().endswith(".exe"):

                subprocess.Popen([target], shell=False)

            else:

                subprocess.Popen(target, shell=True)

            return True, f"{app} opened successfully."

        except Exception as error:

            return False, str(error)

    def close(self, app):

        app = self.normalize(app)

        path = self.find_application(app)

        exe = Path(path).name if path and not path.startswith("shell:") else app

        if not exe.lower().endswith(".exe"):
            exe += ".exe"

        try:

            result = subprocess.run(
                ["taskkill", "/F", "/IM", exe],
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

        except Exception as error:

            return False, str(error)

        if result.returncode == 0:
            return True, f"{app} closed successfully."

        return False, f"{app} is not running."
