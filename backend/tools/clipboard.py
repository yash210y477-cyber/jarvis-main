"""Clipboard read/write through PowerShell (no extra dependency)."""

import subprocess


POWERSHELL = ["powershell", "-NoProfile", "-NonInteractive", "-Command"]

GET_SCRIPT = "Get-Clipboard -Raw"

SET_SCRIPT = "Set-Clipboard -Value ([Console]::In.ReadToEnd())"

MAX_CHARS = 4000


def _run(args, stdin=None):

    return subprocess.run(
        POWERSHELL + [args],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=15,
    )


def get_clipboard() -> dict:

    try:

        completed = _run(GET_SCRIPT)

    except Exception as error:

        return {"success": False, "error": str(error)}

    if completed.returncode != 0:

        return {
            "success": False,
            "error": (completed.stderr or "Could not read the clipboard.").strip(),
        }

    text = completed.stdout or ""

    return {
        "success": True,
        "content": text[:MAX_CHARS],
        "truncated": len(text) > MAX_CHARS,
        "characters": len(text),
    }


def set_clipboard(text: str) -> dict:

    text = "" if text is None else str(text)

    try:

        completed = _run(SET_SCRIPT, stdin=text)

    except Exception as error:

        return {"success": False, "error": str(error)}

    if completed.returncode != 0:

        return {
            "success": False,
            "error": (completed.stderr or "Could not write the clipboard.").strip(),
        }

    return {"success": True, "characters": len(text)}
