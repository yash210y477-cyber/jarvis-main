"""Look at the user's screen and explain what is on it.

The screenshot is taken with the same helper the screenshot tool uses, then the
picture goes to the vision model (GLM-5V-Turbo) together with the user's own
question, so "yeh page kya hai" and "summarize this page" both work.
"""

import io
import logging
from pathlib import Path

from config.settings import settings
from tools import screenshot, vision

logger = logging.getLogger(__name__)

# A full desktop PNG is heavy; the vision model needs no more than this.
MAX_WIDTH = 1600
JPEG_QUALITY = 82

DEFAULT_QUESTION = (
    "Explain what is on this screen to the user. If a website is open, say what "
    "the page is about and summarise its main content in a few short points. "
    "Mention the app or site name if you can read it."
)


def shrink(image_path: str) -> Path:
    """A smaller JPEG copy of the screenshot (or the original if PIL fails)."""

    source = Path(image_path)

    try:

        from PIL import Image

        with Image.open(source) as image:

            if image.width > MAX_WIDTH:

                ratio = MAX_WIDTH / image.width

                image = image.resize(
                    (MAX_WIDTH, max(1, int(image.height * ratio))),
                    Image.LANCZOS,
                )

            if image.mode != "RGB":

                image = image.convert("RGB")

            buffer = io.BytesIO()

            image.save(buffer, format="JPEG", quality=JPEG_QUALITY)

        target = source.with_suffix(".jpg")

        target.write_bytes(buffer.getvalue())

        return target

    except Exception as error:

        logger.info("Screen shrink skipped: %s", error)

        return source


def read_screen(question: str = "", label: str = "vision") -> dict:
    """Capture the screen and return the vision model's explanation."""

    shot = screenshot.capture_screen(label)

    if not shot.get("success"):

        return {
            "success": False,
            "error": shot.get("error") or "Screen capture failed.",
        }

    image = shrink(shot["path"])

    answer = vision.see(question or DEFAULT_QUESTION, str(image))

    if not answer.get("success"):

        error = str(answer.get("error") or "The vision model did not answer.")

        text = error.lower()

        if any(word in text for word in ("insufficient", "balance", "recharge", "402", "429")):

            error = (
                "No free vision model could answer (z.ai and the OpenRouter "
                "fallback both failed). Check ZAI_API_KEY and "
                "OPENROUTER_VISION_MODELS."
            )

        return {
            "success": False,
            "path": shot["path"],
            "error": error,
        }

    return {
        "success": True,
        "path": shot["path"],
        "model": answer.get("model"),
        "answer": answer.get("answer", ""),
        "image": str(image),
        "max_width": MAX_WIDTH,
    }
