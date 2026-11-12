"""Open folders, files and built-in Windows apps."""

import os
import subprocess
from pathlib import Path

from config.settings import settings


HOME = Path.home()

FOLDER_ALIASES = {
    "desktop": HOME / "Desktop",
    "downloads": HOME / "Downloads",
    "download": HOME / "Downloads",
    "documents": HOME / "Documents",
    "docs": HOME / "Documents",
    "pictures": HOME / "Pictures",
    "photos": HOME / "Pictures",
    "music": HOME / "Music",
    "songs": HOME / "Music",
    "videos": HOME / "Videos",
    "home": HOME,
    "user": HOME,
    "workspace": Path(settings.WORKSPACE_ROOT),
    "project": Path(settings.WORKSPACE_ROOT),
    "jarvis": Path(settings.WORKSPACE_ROOT),
    "recycle bin": Path("C:/$Recycle.Bin"),
}

# Protocol handlers registered by the Windows apps themselves.
SPECIAL_APPS = {
    "alarm": ("ms-clock:", "shell:AppsFolder\\Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"),
    "alarms": ("ms-clock:", "shell:AppsFolder\\Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"),
    "clock": ("ms-clock:", "shell:AppsFolder\\Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"),
    "timer": ("ms-clock:", "shell:AppsFolder\\Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"),
    "stopwatch": ("ms-clock:", "shell:AppsFolder\\Microsoft.WindowsAlarms_8wekyb3d8bbwe!App"),
    "settings": ("ms-settings:", None),
    "camera": ("microsoft.windows.camera:", None),
    "calculator": ("calculator:", None),
    "photos": ("ms-photos:", None),
    "store": ("ms-windows-store:", None),
}

# Folder search: where a spoken folder name is looked up, and how deep.
SEARCH_DEPTHS = {
    "home": 5,
    "drive": 3,
}

SKIP_DIRS = {
    "appdata", "windows", "node_modules", ".git", "$recycle.bin",
    "program files", "program files (x86)", "programdata",
    "system volume information", "xampp", "tomcat", "drivers",
}

MAX_SCANNED = 20000

_FOLDER_CACHE = {}


def _clean(path_text: str) -> str:

    text = (path_text or "").strip().strip("\"'")

    cleaned = text.lower()

    for noise in (
        " folder", " directory", " please", " abhi", " kholo", " khol",
        " khol do", " open", " the ",
    ):

        cleaned = cleaned.replace(noise, " ")

    return " ".join(cleaned.split())


def _exact(folder: str, needle: str) -> bool:

    name = folder.lower().replace("-", " ").replace("_", " ").strip()

    wanted = needle.replace("-", " ").replace("_", " ").strip()

    return name == wanted or name.replace(" ", "") == wanted.replace(" ", "")


def _matches(folder: str, needle: str) -> bool:

    name = folder.lower().replace("-", " ").replace("_", " ").strip()

    wanted = needle.replace("-", " ").replace("_", " ").strip()

    if name == wanted:
        return True

    if name.replace(" ", "") == wanted.replace(" ", ""):
        return True

    # "work" should still find "Work Projects"
    return name.startswith(wanted) and len(name) - len(wanted) <= 12


def _collect(needle: str, roots, allow_prefix: bool, budget):

    best = None
    best_depth = 10 ** 6

    for root, depth in roots:

        if not root.exists():
            continue

        stack = [(root, 0)]

        while stack:

            current, level = stack.pop()

            if level >= depth:
                continue

            try:

                with os.scandir(current) as entries:

                    for entry in entries:

                        budget[0] += 1

                        if budget[0] > MAX_SCANNED:
                            return best

                        try:

                            if not entry.is_dir():
                                continue

                        except OSError:
                            continue

                        name = entry.name

                        if name.lower() in SKIP_DIRS or name.startswith((".", "$")):
                            continue

                        if allow_prefix or _exact(name, needle):

                            if _matches(name, needle):

                                found_depth = level + 1

                                if found_depth < best_depth:

                                    best = Path(entry.path)
                                    best_depth = found_depth

                        stack.append((Path(entry.path), level + 1))

            except (PermissionError, OSError):
                continue

    return best


def _search_folder(needle: str):

    cached = _FOLDER_CACHE.get(needle)

    if cached is not None:
        return cached

    roots = []

    for name in ("Desktop", "Downloads", "Documents", "Pictures", "Videos", "Music"):

        folder = HOME / name

        if folder.exists():
            roots.append((folder, SEARCH_DEPTHS["home"]))

    roots.append((HOME, SEARCH_DEPTHS["home"]))
    roots.append((Path(settings.WORKSPACE_ROOT), SEARCH_DEPTHS["home"]))

    user_roots = list(roots)

    for letter in "CDEFGH":

        drive = Path(letter + ":/")

        if drive.exists():
            roots.append((drive, SEARCH_DEPTHS["drive"]))

    budget = [0]

    # An exact name anywhere wins; among those the shallowest, so "work"
    # resolves to D:\work rather than some deep folder that merely contains it.
    found = _collect(needle, roots, False, budget)

    if found is None:

        # Otherwise allow "work" to match "Work Projects", near the user only.
        found = _collect(needle, user_roots, True, budget)

    _FOLDER_CACHE[needle] = found

    return found


def resolve(path_text: str):
    """Turn a spoken path or folder name into a real Path."""

    target_text = (path_text or "").strip().strip("\"'")

    if not target_text:
        return None

    cleaned = _clean(target_text)

    alias = FOLDER_ALIASES.get(cleaned)

    if alias is not None:
        return alias

    expanded = Path(os.path.expandvars(os.path.expanduser(target_text)))

    if expanded.is_absolute() and expanded.exists():
        return expanded

    workspace = Path(settings.WORKSPACE_ROOT)

    for base in (workspace, Path.cwd(), HOME):

        candidate = base / expanded

        if candidate.exists():
            return candidate

    if not cleaned:
        return None

    found = _search_folder(cleaned)

    if found is not None:
        return found

    if expanded.is_absolute():
        return expanded

    return None


def open_path(path=""):

    target = resolve(path)

    if target is None:
        return {
            "success": False,
            "path": path,
            "error": f"I couldn't find `{path}` on this computer.",
        }

    if not target.exists():
        return {
            "success": False,
            "path": str(target),
            "error": f"`{target}` does not exist.",
        }

    try:

        os.startfile(str(target))

    except OSError as error:

        return {"success": False, "path": str(target), "error": str(error)}

    kind = "folder" if target.is_dir() else "file"

    return {
        "success": True,
        "path": str(target),
        "kind": kind,
        "message": f"Opening the {kind} `{target}`.",
    }


def open_special(app=""):

    key = (app or "").strip().lower()

    for suffix in (" app", " application"):

        key = key.replace(suffix, "")

    entry = SPECIAL_APPS.get(key)

    if not entry:

        return {
            "success": False,
            "app": key,
            "error": f"I don't know the Windows {app} app.",
        }

    uri, shell_path = entry

    try:

        os.startfile(uri)

    except OSError:

        if not shell_path:

            return {
                "success": False,
                "app": key,
                "error": f"Could not open {app}.",
            }

        try:

            subprocess.Popen(["explorer.exe", shell_path], shell=False)

        except OSError as error:

            return {"success": False, "app": key, "error": str(error)}

    return {
        "success": True,
        "app": key,
        "message": f"Opening {key}.",
    }
