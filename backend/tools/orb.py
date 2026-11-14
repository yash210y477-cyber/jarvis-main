"""A small always-on-top orb beside the cursor that shows what JARVIS is doing.

idle / listening / thinking / speaking are written to a state file by the rest
of the app; a separate process reads it and paints the orb, so nothing in the
backend has to touch a UI toolkit.
"""

import json
import logging
import subprocess
import sys
import time
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)

DATA = Path(settings.WORKSPACE_ROOT) / "backend" / "data" / "orb"
STATE_FILE = DATA / "state.json"

COLORS = {
    "idle": "#2b5876",
    "listening": "#00e5ff",
    "thinking": "#ffb347",
    "speaking": "#6dff9b",
    "error": "#ff5c5c",
}

ORB_SCRIPT = r"""
import ctypes, json, os, time, tkinter as tk

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

state_file = r"{state_file}"
COLORS = {colors}
user32 = ctypes.windll.user32

class Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-transparentcolor", "black")
root.configure(bg="black")
size = 210
canvas = tk.Canvas(root, width=size, height=size, bg="black",
                   highlightthickness=0)
canvas.pack()

def read_state():
    try:
        with open(state_file, encoding="utf-8") as handle:
            return json.load(handle)
    except Exception:
        return {{"state": "idle", "text": ""}}

def draw():
    data = read_state()
    name = data.get("state") or "idle"
    color = COLORS.get(name, COLORS["idle"])
    text = (data.get("text") or "")[:26]

    point = Point()
    user32.GetCursorPos(ctypes.byref(point))
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    pos_x = min(max(0, point.x + 18), screen_w - size)
    pos_y = min(max(0, point.y + 16), screen_h - size)
    root.geometry("{{0}}x{{1}}+{{2}}+{{3}}".format(size, size, pos_x, pos_y))

    canvas.delete("all")
    canvas.create_oval(6, 6, 34, 34, outline="", fill="#0a1420")
    canvas.create_oval(10, 10, 30, 30, outline=color, width=2)
    canvas.create_oval(16, 16, 24, 24, outline="", fill=color)

    if text:
        canvas.create_rectangle(4, 40, min(size - 4, 12 + len(text) * 8), 62,
                                fill="#04070d", outline=color)
        canvas.create_text(10, 51, text=text, anchor="w", fill="#eaf6ff",
                           font=("Segoe UI", 8))

    root.after(120, draw)

root.attributes("-alpha", 0.95)
draw()
root.mainloop()
"""


def set_state(state: str, text: str = "") -> None:
    """Record what JARVIS is doing so the orb can paint it."""

    try:

        DATA.mkdir(parents=True, exist_ok=True)

        temp = STATE_FILE.with_suffix(".tmp")

        temp.write_text(
            json.dumps({"state": state, "text": (text or "")[:60], "ts": time.time()}),
            encoding="utf-8",
        )

        temp.replace(STATE_FILE)

    except Exception as error:

        logger.info("Orb state skipped: %s", error)


def get_state() -> dict:

    try:

        return json.loads(STATE_FILE.read_text(encoding="utf-8"))

    except Exception:

        return {"state": "idle", "text": ""}


_PROCESS = None


def is_running() -> bool:

    return _PROCESS is not None and _PROCESS.poll() is None


def start() -> dict:
    """Show the orb (idempotent)."""

    global _PROCESS

    if is_running():

        return {"success": True, "message": "The orb is already on screen."}

    try:

        DATA.mkdir(parents=True, exist_ok=True)

        if not STATE_FILE.exists():

            set_state("idle", "")

        script = ORB_SCRIPT.format(
            state_file=str(STATE_FILE).replace("\\", "\\\\"),
            colors=json.dumps(COLORS),
        )

        _PROCESS = subprocess.Popen(
            [sys.executable, "-c", script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        return {"success": True, "message": "The orb is on screen."}

    except Exception as error:

        logger.info("Orb skipped: %s", error)

        _PROCESS = None

        return {"success": False, "error": str(error)}


def stop() -> dict:

    global _PROCESS

    if not is_running():

        _PROCESS = None

        return {"success": True, "message": "The orb is not running."}

    try:

        _PROCESS.terminate()

        _PROCESS.wait(timeout=5)

    except Exception as error:

        logger.info("Orb stop issue: %s", error)

    finally:

        _PROCESS = None

    return {"success": True, "message": "Orb closed."}
