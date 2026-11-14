"""A small answer card that sits beside what the user is reading.

The card is its own always-on-top window, so the reply appears next to the
page instead of in the chat panel. It is plain text laid out nicely: a title,
bullets and short lines. Click it or press Esc to close, or let it fade on its
own after `seconds`.
"""

import json
import logging
import subprocess
import sys
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

CARD_SCRIPT = r"""
import ctypes, json, tkinter as tk

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

with open(r"{payload}", encoding="utf-8") as handle:
    data = json.load(handle)

title = data.get("title") or ""
body = data.get("body") or ""
width = int(data.get("width") or 400)
seconds = int(data.get("seconds") or 25)
side = data.get("side") or "right"

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.configure(bg="#04070d")

screen_w = root.winfo_screenwidth()
screen_h = root.winfo_screenheight()

x = screen_w - width - 48 if side == "right" else 48
y = max(80, screen_h // 4)

root.geometry("{}x60+{}+{}".format(width, x, y))

frame = tk.Frame(root, bg="#04070d", highlightbackground="#00e5ff",
                 highlightthickness=1)
frame.pack(fill="both", expand=True)

label_title = tk.Label(frame, text=title, bg="#04070d", fg="#00e5ff",
                       font=("Segoe UI", 12, "bold"), anchor="w",
                       justify="left", wraplength=width - 32)
label_title.pack(fill="x", padx=16, pady=(0, 6))

label_body = tk.Label(frame, text=body, bg="#04070d", fg="#eaf6ff",
                      font=("Segoe UI", 10), anchor="w", justify="left",
                      wraplength=width - 32)
label_body.pack(fill="both", expand=True, padx=16)

hint = tk.Label(frame, text="click or Esc to close", bg="#04070d", fg="#4a6b80",
                font=("Segoe UI", 8), anchor="e")
hint.pack(fill="x", padx=16, pady=(4, 10))

root.update_idletasks()
height = min(max(120, frame.winfo_reqheight()), int(screen_h * 0.6))
root.geometry("{}x{}+{}+{}".format(width, height, x, y))

def close(event=None):
    root.destroy()

for widget in (root, frame, label_title, label_body, hint):
    widget.bind("<Button-1>", close)

root.bind("<Escape>", close)
root.after(max(4000, seconds * 1000), close)
root.mainloop()
"""


def show_card(
    title: str = "JARVIS",
    text: str = "",
    seconds: int = 25,
    width: int = 400,
    side: str = "right",
):
    """Best effort: a failed card must never break the reply itself."""

    if not (text or "").strip():

        return {"success": False, "error": "Nothing to show."}

    try:

        payload = Path(tempfile.gettempdir()) / f"jarvis-card-{int(time.time() * 1000)}.json"

        payload.write_text(
            json.dumps(
                {
                    "title": title or "JARVIS",
                    "body": text,
                    "seconds": int(seconds),
                    "width": int(width),
                    "side": side,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        script = CARD_SCRIPT.replace("{payload}", str(payload).replace("\\", "\\\\"))

        subprocess.Popen(
            [sys.executable, "-c", script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

        return {"success": True, "action": "card", "message": "Answer card on screen."}

    except Exception as error:

        logger.info("Answer card skipped: %s", error)

        return {"success": False, "error": str(error)}
