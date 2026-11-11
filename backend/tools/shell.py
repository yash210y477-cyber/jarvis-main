"""Shell tool with an allowlist and a confirmation gate.

Only known-safe executables run, destructive patterns are rejected outright,
and the tool is registered as CONFIRM so the user sees the exact command first.
"""

import re
import shlex
import subprocess
from pathlib import Path

from config.settings import settings


ALLOWED_COMMANDS = {
    "dir", "ls", "echo", "type", "cat", "where", "which", "whoami", "hostname",
    "ipconfig", "ifconfig", "ping", "tasklist", "systeminfo", "ver", "date",
    "time", "git", "python", "py", "pip", "node", "npm", "npx", "pytest",
    "ffmpeg", "winget", "code", "notepad", "start",
}

DENIED_PATTERNS = [
    r"\brm\s+-r", r"\brm\s+-f", r"\bdel\s+/[sq]", r"\brd\s+/s", r"\bformat\b",
    r"\bshutdown\b", r"\breboot\b", r"\breg\s+(add|delete)\b", r"\bnet\s+user\b",
    r"\btakeown\b", r"\bicacls\b", r"\bbcdedit\b", r"\bdiskpart\b",
    r"\bcurl\b.*\|\s*(sh|bash)", r"\bpowershell\b.*-enc", r"\bsc\s+(delete|config)\b",
    r"\btaskkill\b", r"\bwmic\b.*delete", r"\bmkfs\b", r"\bdd\s+if=",
    r">\s*[A-Za-z]:\\Windows", r"\bchmod\s+777\b",
]

MAX_TIMEOUT = 30


def _denied(command: str) -> str:

    lower = command.lower()

    for pattern in DENIED_PATTERNS:

        if re.search(pattern, lower):

            return pattern

    return ""


def run_command(command: str, timeout: int = 15) -> dict:

    command = (command or "").strip()

    if not command:

        return {"success": False, "error": "Empty command."}

    try:

        parts = shlex.split(command, posix=False)

    except ValueError as error:

        return {"success": False, "error": f"Could not parse command: {error}"}

    if not parts:

        return {"success": False, "error": "Empty command."}

    executable = Path(parts[0]).name.lower()

    if executable.endswith(".exe"):

        executable = executable[:-4]

    if executable not in ALLOWED_COMMANDS:

        return {
            "success": False,
            "error": (
                f"`{executable}` is not on the allowlist. Allowed: "
                + ", ".join(sorted(ALLOWED_COMMANDS))
            ),
        }

    blocked = _denied(command)

    if blocked:

        return {
            "success": False,
            "error": f"Command matches a blocked pattern: {blocked}",
        }

    limit = max(1, min(int(timeout), MAX_TIMEOUT))

    try:

        completed = subprocess.run(
            parts,
            cwd=str(Path(settings.WORKSPACE_ROOT)),
            capture_output=True,
            text=True,
            timeout=limit,
            shell=False,
        )

    except subprocess.TimeoutExpired:

        return {"success": False, "error": f"Command timed out after {limit}s."}

    except FileNotFoundError:

        return {"success": False, "error": f"`{parts[0]}` is not installed."}

    except OSError as error:

        return {"success": False, "error": str(error)}

    return {
        "success": completed.returncode == 0,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "")[:4000],
        "stderr": (completed.stderr or "")[:2000],
    }
