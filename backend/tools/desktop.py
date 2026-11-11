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


def resolve(path_text: str):
    """Turn a spoken path or folder name into a real Path."""

    text = (path_text or "").strip().strip("\"'")

    if not text:

        return None

    cleaned = text.lower()

    for noise in (" folder", " directory", " please", " abhi", " kholo", " khol"):

        cleaned = cleaned.replace(noise, "")

    cleaned = cleaned.strip()

    alias = FOLDER_ALIASES.get(cleaned)

    if alias is not None:

        return alias

    expanded = Path(os.path.expandvars(os.path.expanduser(text)))

    if expanded.is_absolute():

        return expanded

    workspace = Path(settings.WORKSPACE_ROOT)

    for base in (workspace, Path.cwd(), HOME):

        candidate = base / expanded

        if candidate.exists():

            return candidate

    # A relative name that exists nowhere is still reported as not found.
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
