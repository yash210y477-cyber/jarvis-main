"""Files Jarvis makes: shown in the chat, copied to Downloads only on request.

Same idea as generated pictures: nothing lands in the user's Downloads folder
until the Download button in the chat is pressed.
"""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from tools import files as store

router = APIRouter()


def downloads_dir() -> Path:
    """The user's Downloads/Jarvis folder, made on first use."""

    folder = Path.home() / "Downloads" / "Jarvis"
    folder.mkdir(parents=True, exist_ok=True)

    return folder


def _target(name: str) -> Path:
    """A real file inside the workspace, or a clear refusal."""

    try:
        path = store._resolve(name)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error))

    if not path.is_file():
        raise HTTPException(status_code=404, detail="No such file")

    return path


@router.get("/files/{name:path}")
def get_file(name: str):
    """The file itself, so the chat can offer it as a download."""

    path = _target(name)

    return FileResponse(path, filename=path.name)


@router.post("/files/{name:path}/download")
def download_file(name: str):
    """Copy one generated file into Downloads/Jarvis, on request."""

    path = _target(name)

    try:
        target = downloads_dir() / path.name
        target.write_bytes(path.read_bytes())
    except Exception as error:
        return {"success": False, "error": f"Could not save the file: {error}"}

    return {
        "success": True,
        "path": str(target),
        "message": f"Saved to {target}",
    }
