"""Draw a picture through OpenRouter and keep it in a throwaway cache."""

import base64
import json
import logging
import os
import tempfile
import time
from pathlib import Path

import requests

from config.settings import settings

log = logging.getLogger(__name__)

URL = "https://openrouter.ai/api/v1/images"
MODEL = settings.IMAGE_MODEL

# OpenRouter gives 50 free requests a day across every free model, and drawing
# is the first thing to hit that wall. This keyless service keeps the drawing
# tool working until the quota returns; IMAGE_FALLBACK=0 turns it off.
FALLBACK_URL = "https://image.pollinations.ai/prompt"
FALLBACK_MODEL = "flux"


CACHE_HOURS = 24


def images_dir() -> Path:
    """Where fresh pictures wait for the Download button.

    This is a throwaway cache in the temp folder, never the data folder: the
    only copy that stays on the machine is the one saved into Downloads/Jarvis.
    """

    folder = Path(tempfile.gettempdir()) / "jarvis-images"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _fallback_enabled() -> bool:
    return (os.getenv("IMAGE_FALLBACK", "1") or "1").strip().lower() not in (
        "0",
        "off",
        "false",
        "no",
    )


def _quota_reset_hint(detail: str) -> str:
    """The local time the free daily quota comes back, when the reply says so."""

    try:

        payload = json.loads(detail or "{}")

    except Exception:

        return ""

    try:

        reset = payload["error"]["metadata"]["headers"]["X-RateLimit-Reset"]

        when = time.strftime("%d %b %H:%M", time.localtime(int(reset) / 1000))

        return f" The free image quota returns at {when}."

    except Exception:

        return ""


def _fallback_image(prompt: str):
    """Draw with the keyless service used when the free quota is spent."""

    if not _fallback_enabled():

        return None

    import urllib.parse

    base = (os.getenv("IMAGE_FALLBACK_URL") or FALLBACK_URL).rstrip("/")
    model = (os.getenv("IMAGE_FALLBACK_MODEL") or FALLBACK_MODEL).strip()

    url = (
        f"{base}/{urllib.parse.quote(prompt)}"
        f"?width=1024&height=1024&nologo=true&model={model}"
    )

    try:

        response = requests.get(url, timeout=240)

    except Exception as error:

        return {"success": False, "error": f"Fallback image service unreachable: {error}"}

    if response.status_code != 200 or not (response.headers.get("content-type") or "").startswith("image"):

        detail = (response.text or "").strip().replace("\n", " ")[:200]

        return {
            "success": False,
            "error": f"Fallback image service returned {response.status_code}: {detail}",
        }

    prune()

    path = images_dir() / f"{time.strftime('%Y%m%d-%H%M%S')}-1.png"

    try:

        import io

        from PIL import Image

        picture = Image.open(io.BytesIO(response.content))
        picture.convert("RGB").save(path, format="PNG")

    except Exception as error:

        return {"success": False, "error": f"Fallback picture could not be saved: {error}"}

    return {
        "success": True,
        "action": "generate_image",
        "prompt": prompt,
        "path": str(path),
        "paths": [str(path)],
        "images": [f"/images/{path.name}"],
        "count": 1,
        "provider": f"pollinations/{model}",
        "message": f"Image ready: {path.name} (fallback: {model}, free quota spent)",
    }


def prune(hours: int = CACHE_HOURS) -> None:
    """Drop pictures nobody downloaded, so the cache never grows forever."""

    cutoff = time.time() - hours * 3600

    for path in images_dir().glob("*.png"):

        try:

            if path.stat().st_mtime < cutoff:

                path.unlink()

        except OSError:

            pass


def generate_image(prompt: str, model: str = ""):
    """Generate one image from a text prompt (OpenRouter images API)."""

    # Nothing is opened or copied anywhere: the picture waits in the temp
    # cache and goes back to the chat, where the user decides whether to
    # download it.

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

        # A spent free quota is not a broken model: draw through the keyless
        # service and say why, so the tool still does its job today.
        if response.status_code in (402, 429):

            drawn = _fallback_image(prompt)

            if drawn is not None:

                return drawn

            return {
                "success": False,
                "error": (
                    f"OpenRouter returned {response.status_code}: {detail}"
                    + _quota_reset_hint(detail)
                ),
            }

        return {
            "success": False,
            "error": f"OpenRouter returned {response.status_code}: {detail}",
        }

    try:

        items = (response.json() or {}).get("data") or []

    except Exception as error:

        return {"success": False, "error": f"Unreadable OpenRouter reply: {error}"}

    prune()

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
