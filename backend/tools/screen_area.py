"""Ask about one part of the screen instead of all of it.

The user presses the shortcut, drags a box over whatever they are reading and
the vision model explains just that box. The selection happens in a separate
transparent process, so no window of ours stays on top of their work.
"""

import json
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from tools import screenshot

logger = logging.getLogger(__name__)

SELECT_MS = 120000

SELECT_SCRIPT = r"""
import ctypes, json, tkinter as tk

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

target = r"{target}"

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-alpha", 0.28)
root.geometry("{{w}}x{{h}}+{{l}}+{{t}}".format(w={w}, h={h}, l={left}, t={top}))
root.configure(bg="#04070d")
canvas = tk.Canvas(root, bg="#04070d", highlightthickness=0, cursor="crosshair")
canvas.pack(fill="both", expand=True)
canvas.create_text({cx}, 40, text="Drag a box around what you want explained  (Esc to cancel)",
                   fill="#00e5ff", font=("Segoe UI", 15, "bold"))
state = {{"start": None, "rect": None}}
box = {{"id": None}}

def save(rect):
    with open(target, "w", encoding="utf-8") as handle:
        json.dump(rect, handle)
    root.destroy()

def down(event):
    state["start"] = (event.x, event.y)
    if box["id"]:
        canvas.delete(box["id"])

def move(event):
    if not state["start"]:
        return
    x0, y0 = state["start"]
    if box["id"]:
        canvas.delete(box["id"])
    box["id"] = canvas.create_rectangle(x0, y0, event.x, event.y,
                                       outline="#00e5ff", width=2)

def up(event):
    if not state["start"]:
        return
    x0, y0 = state["start"]
    rect = {{"x": min(x0, event.x), "y": min(y0, event.y),
             "w": abs(event.x - x0), "h": abs(event.y - y0)}}
    if rect["w"] < 12 or rect["h"] < 12:
        state["start"] = None
        return
    save(rect)

canvas.bind("<ButtonPress-1>", down)
canvas.bind("<B1-Motion>", move)
canvas.bind("<ButtonRelease-1>", up)
root.bind("<Escape>", lambda event: save(None))
root.after({ms}, lambda: save(None))
root.mainloop()
"""


def select_region(ms: int = SELECT_MS) -> dict:
    """Let the user drag a rectangle on the whole desktop; return it or None."""

    shot = screenshot.capture_screen("area")

    if not shot.get("success"):

        return {"success": False, "error": shot.get("error") or "Screen capture failed."}

    left = int(shot.get("left") or 0)
    top = int(shot.get("top") or 0)
    width = int(shot.get("width") or 0)
    height = int(shot.get("height") or 0)

    if not width or not height:

        from PIL import Image

        with Image.open(shot["path"]) as image:

            width, height = image.size

    target = Path(tempfile.gettempdir()) / f"jarvis-area-{int(time.time() * 1000)}.json"

    script = SELECT_SCRIPT.format(
        target=str(target).replace("\\", "\\\\"),
        w=width,
        h=height,
        left=left,
        top=top,
        cx=width // 2,
        ms=int(ms),
    )

    try:

        subprocess.run(
            [sys.executable, "-c", script],
            timeout=max(5, ms // 1000 + 5),
        )

    except subprocess.TimeoutExpired:

        logger.info("Area selection timed out.")

    rect = None

    if target.exists():

        try:

            rect = json.loads(target.read_text(encoding="utf-8"))

        except Exception as error:

            logger.info("Area selection unreadable: %s", error)

        finally:

            try:

                target.unlink()

            except OSError:

                pass

    return {"success": True, "path": shot["path"], "rect": rect}


def crop(path: str, rect: dict, left: int = 0, top: int = 0) -> Path:
    """Cut the selected box out of the screenshot (physical pixels)."""

    from PIL import Image

    source = Path(path)

    box = (
        max(0, int(rect["x"]) - int(left)),
        max(0, int(rect["y"]) - int(top)),
        max(0, int(rect["x"]) - int(left) + int(rect["w"])),
        max(0, int(rect["y"]) - int(top) + int(rect["h"])),
    )

    with Image.open(source) as image:

        if image.mode != "RGB":

            image = image.convert("RGB")

        piece = image.crop(box)

        target = source.with_name(source.stem + "-area.png")

        piece.save(target, format="PNG")

    return target


def ask_area(question: str = "") -> dict:
    """Select, crop, then let the vision model explain the selection."""

    picked = select_region()

    if not picked.get("success"):

        return {"success": False, "error": picked.get("error") or "Screen capture failed."}

    rect = picked.get("rect")

    if not rect:

        return {"success": False, "error": "No area was selected."}

    area = crop(picked["path"], rect)

    from providers.zai import ZaiProvider

    answer = ZaiProvider().see(
        question
        or "Explain this part of the screen to the user in a few short points.",
        str(area),
    )

    if not answer.get("success"):

        error = str(answer.get("error") or "The vision model did not answer.")

        if any(word in error.lower() for word in ("insufficient", "balance", "402", "429")):

            error = (
                "The z.ai account has no balance for the vision model. "
                "Recharge z.ai and ask again."
            )

        return {"success": False, "error": error, "image": str(area), "rect": rect}

    return {
        "success": True,
        "image": str(area),
        "rect": rect,
        "model": answer.get("model"),
        "answer": (answer.get("answer") or "").strip(),
    }
