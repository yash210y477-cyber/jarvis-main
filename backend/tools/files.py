"""Sandboxed file access for the agent.

Every path is resolved inside WORKSPACE_ROOT; anything that escapes it (via
"..", an absolute path elsewhere, a symlink) is rejected before touching disk.
"""

from pathlib import Path

from config.settings import settings


BLOCKED_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".idea", ".vscode",
}

BLOCKED_SUFFIXES = {".pyc", ".pyo", ".exe", ".dll", ".pyd", ".so"}

MAX_READ_CHARS = 20000
MAX_WRITE_CHARS = 200000


def workspace_root() -> Path:

    return Path(settings.WORKSPACE_ROOT).resolve()


def _resolve(path: str) -> Path:

    root = workspace_root()

    raw = (path or ".").strip().strip('"').strip("'")

    candidate = Path(raw)

    target = candidate if candidate.is_absolute() else root / candidate

    target = target.resolve()

    if target != root and root not in target.parents:

        raise ValueError(f"Path is outside the workspace: {path}")

    parts = {part.lower() for part in target.parts}

    if parts & BLOCKED_DIRS:

        raise ValueError(f"Path is in a blocked directory: {path}")

    if target.suffix.lower() in BLOCKED_SUFFIXES:

        raise ValueError(f"File type is blocked: {target.suffix}")

    return target


def _relative(path: Path) -> str:

    try:

        return str(path.relative_to(workspace_root()))

    except ValueError:

        return str(path)


def list_files(path: str = ".", limit: int = 100) -> dict:

    try:

        target = _resolve(path)

    except ValueError as error:

        return {"success": False, "error": str(error)}

    if not target.exists():

        return {"success": False, "error": f"Not found: {path}"}

    if target.is_file():

        return {
            "success": True,
            "path": _relative(target),
            "files": [{
                "name": target.name,
                "type": "file",
                "size": target.stat().st_size,
            }],
        }

    entries = []
    skipped = 0

    for item in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):

        if item.name.lower() in BLOCKED_DIRS:

            skipped += 1

            continue

        if len(entries) >= limit:

            skipped += 1

            continue

        try:

            size = item.stat().st_size if item.is_file() else None

        except OSError:

            size = None

        entries.append({
            "name": item.name,
            "type": "file" if item.is_file() else "dir",
            "size": size,
        })

    return {
        "success": True,
        "path": _relative(target),
        "files": entries,
        "truncated": skipped > 0,
    }


def read_file(path: str, max_chars: int = MAX_READ_CHARS) -> dict:

    try:

        target = _resolve(path)

    except ValueError as error:

        return {"success": False, "error": str(error)}

    if not target.exists() or not target.is_file():

        return {"success": False, "error": f"Not a file: {path}"}

    try:

        text = target.read_text(encoding="utf-8", errors="replace")

    except OSError as error:

        return {"success": False, "error": str(error)}

    limit = max(200, min(int(max_chars), MAX_READ_CHARS))

    clipped = len(text) > limit

    return {
        "success": True,
        "path": _relative(target),
        "content": text[:limit],
        "truncated": clipped,
        "lines": text.count("\n") + 1,
    }


def write_file(path: str, content: str, append: bool = False) -> dict:

    try:

        target = _resolve(path)

    except ValueError as error:

        return {"success": False, "error": str(error)}

    if len(content or "") > MAX_WRITE_CHARS:

        return {
            "success": False,
            "error": f"Content is larger than {MAX_WRITE_CHARS} characters.",
        }

    try:

        target.parent.mkdir(parents=True, exist_ok=True)

        with target.open("a" if append else "w", encoding="utf-8") as handle:

            handle.write(content or "")

    except OSError as error:

        return {"success": False, "error": str(error)}

    return {
        "success": True,
        "path": _relative(target),
        "bytes": target.stat().st_size,
        "mode": "append" if append else "write",
    }
