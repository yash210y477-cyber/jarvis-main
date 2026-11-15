"""Draw a picture through OpenRouter and keep it in the data folder."""

import base64
import json
import logging
import os
import subprocess
import time
from pathlib import Path

import requests

from config.settings import settings
from memory.storage import data_dir

log = logging.getLogger(__name__)

URL = "https://openrouter.ai/api/v1/images"
MODEL = settings.IMAGE_MODEL


def images_dir() -> Path:
    folder = data_dir() / "images"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _show(path: Path) -> None:
    """Open the finished picture, so the request ends with a visible result."""

    try:

        if os.name == "nt":

            os.startfile(str(path))

        else:

            subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL)

    except Exception as error:

        log.debug("Could not open %s: %s", path, error)


def generate_image(prompt: str, model: str = "", show: bool = False):
    """Generate one image from a text prompt (OpenRouter images API)."""

    # Nothing is opened or copied anywhere: the picture goes back to the chat,
    # where the user decides whether to download it.

    prompt = (prompt or "").strip()

    if not prompt:

        return {"success": False, "error": "Tell me what to draw."}

    key = (os.getenv("OPENROUTER_API_KEY") or "").strip()

    if not key:

        return {
            "success": False,
            "error": "OPENROUTER_API_KEY is not set, so I cannot draw anything.",
        }

    payload = {"model": (model or MODEL).strip(), "prompt": prompt}

    try:

        response = requests.post(
            URL,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload),
            timeout=180,
        )

    except Exception as error:

        return {"success": False, "error": f"Could not reach OpenRouter: {error}"}

    if response.status_code != 200:

        detail = (response.text or "").strip().replace("\n", " ")[:200]

        return {
            "success": False,
            "error": f"OpenRouter returned {response.status_code}: {detail}",
        }

    try:

        items = (response.json() or {}).get("data") or []

    except Exception as error:

        return {"success": False, "error": f"Unreadable OpenRouter reply: {error}"}

    saved = []

    stamp = time.strftime("%Y%m%d-%H%M%S")

    for index, item in enumerate(items):

        encoded = (item or {}).get("b64_json")

        if not encoded:

            continue

        path = images_dir() / f"{stamp}-{index + 1}.png"

        try:

            raw = base64.b64decode(encoded)

            # Providers answer webp/jpeg as often as png, so a decodable image
            # is re-saved as real PNG and the .png name stays honest.
            import io

            from PIL import Image

            try:

                picture = Image.open(io.BytesIO(raw))

                picture.convert("RGB").save(path, format="PNG")

            except Exception:

                path.write_bytes(raw)

        except Exception as error:

            log.warning("Saving image failed: %s", error)

            continue

        saved.append(path)

    if not saved:

        if items and items[0].get("url"):

            return {
                "success": True,
                "prompt": prompt,
                "path": items[0]["url"],
                "paths": [items[0]["url"]],
                "message": f"Here is your image: {items[0]['url']}",
            }

        return {"success": False, "error": "OpenRouter sent no image back."}

    if show:

        _show(saved[0])

    return {
        "success": True,
        "action": "generate_image",
        "prompt": prompt,
        "path": str(saved[0]),
        "paths": [str(path) for path in saved],
        "images": [f"/images/{path.name}" for path in saved],
        "count": len(saved),
        "message": f"Image ready: {saved[0].name}",
    }


def download_dir() -> Path:
    """The user's Downloads/Jarvis folder, made on first use."""

    home = Path.home()
    folder = home / "Downloads" / "Jarvis"
    folder.mkdir(parents=True, exist_ok=True)

    return folder


def save_to_downloads(name: str) -> dict:
    """Copy one generated picture into Downloads/Jarvis (only when asked)."""

    source = images_dir() / Path(str(name)).name

    if not source.is_file():
        return {"success": False, "error": "No such image."}

    try:

        target = download_dir() / source.name
        target.write_bytes(source.read_bytes())

    except Exception as error:

        return {"success": False, "error": f"Could not save the image: {error}"}

    return {
        "success": True,
        "path": str(target),
        "message": f"Saved to {target}",
    }
