"""A screen agent: look, point, say what it is about to do, then do it.

One step is: capture the screen -> ask the vision model what to do next -> draw a
short arrow on the exact spot -> click, type or scroll there. The loop stops when
the model says the goal is done, so "is page pe search karo" works step by step
instead of guessing a blind click.

Actions are numbered in the reply, which is the narration the user hears and
reads: "Step 1: 'Search bar par click kar raha hoon'".
"""

import ctypes
import json
import logging
import re
import threading
import time
import webbrowser
from pathlib import Path

from tools import screen_reader

logger = logging.getLogger(__name__)

MAX_STEPS = 4

ARROW_MS = 1100

PROMPT = """You are JARVIS operating a Windows desktop for the user.

User goal: {goal}

Step {step} of {max_steps}. Earlier steps:
{history}

Look at the screenshot and answer with ONE JSON object, nothing else:

{{"thought": "one short line in the user's language about what you see and will do",
  "action": "click" | "type" | "scroll" | "press" | "open_url" | "answer" | "done",
  "x": integer pixel x inside the screenshot (click only),
  "y": integer pixel y inside the screenshot (click only),
  "text": "text to type, key to press, url to open, or the final answer",
  "amount": integer (scroll only, positive is down)}}

Rules:
- Point at the exact button or field: give its centre in screenshot pixels.
- Use "answer" when the goal was only to explain or read the screen.
- Use "done" when the goal is finished.
- Never invent coordinates outside the screenshot.
"""


# ------------------------------------------------------------------ windows


def _enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def click(x: int, y: int) -> dict:
    """Move the pointer to (x, y) and left click once."""

    _enable_dpi_awareness()

    user32 = ctypes.windll.user32

    user32.SetCursorPos(int(x), int(y))

    time.sleep(0.15)

    user32.mouse_event(0x0002, 0, 0, 0, 0)
    user32.mouse_event(0x0004, 0, 0, 0, 0)

    return {"action": "click", "x": int(x), "y": int(y)}


def scroll(amount: int) -> dict:
    _enable_dpi_awareness()

    user32 = ctypes.windll.user32

    direction = -120 if amount >= 0 else 120

    for _ in range(max(1, min(6, abs(int(amount)) or 1))):

        user32.mouse_event(0x0800, 0, 0, direction, 0)

        time.sleep(0.05)

    return {"action": "scroll", "amount": int(amount)}


def type_text(text: str) -> dict:
    """Paste text, which keeps emoji and newlines intact (SendKeys does not)."""

    from tools import clipboard

    clipboard.set_clipboard(text)

    time.sleep(0.1)

    user32 = ctypes.windll.user32

    user32.keybd_event(0x11, 0, 0, 0)      # ctrl down
    user32.keybd_event(0x56, 0, 0, 0)      # v down
    user32.keybd_event(0x56, 0, 0x0002, 0)
    user32.keybd_event(0x11, 0, 0x0002, 0)

    time.sleep(0.15)

    return {"action": "type", "text": text}


KEYS = {
    "enter": 0x0D,
    "esc": 0x1B,
    "escape": 0x1B,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "down": 0x28,
    "up": 0x26,
}


def press(key: str) -> dict:
    user32 = ctypes.windll.user32

    code = KEYS.get((key or "").strip().lower(), 0x0D)

    user32.keybd_event(code, 0, 0, 0)
    user32.keybd_event(code, 0, 0x0002, 0)

    time.sleep(0.1)

    return {"action": "press", "key": key}


def open_url(url: str) -> dict:
    webbrowser.open(url)

    return {"action": "open_url", "url": url}


# ------------------------------------------------------------------- arrow
# A thin arrow appears where the click will land for a moment. It is drawn on a
# transparent full-screen canvas, so nothing on the desktop changes.

ARROW_SCRIPT = """
import tkinter as tk

root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True)
root.attributes("-transparentcolor", "lightgray")
root.geometry("{w}x{h}+0+0")
root.configure(bg="lightgray")

canvas = tk.Canvas(root, bg="lightgray", highlightthickness=0)
canvas.pack(fill="both", expand=True)

x, y = {x}, {y}

canvas.create_oval(x - 26, y - 26, x + 26, y + 26, outline="#00e5ff", width=3)
canvas.create_line(x + 150, y + 110, x + 30, y + 26, fill="#00e5ff", width=4,
                   arrow="last")
canvas.create_rectangle(x + 140, y + 100, x + 380, y + 148, fill="#04070d",
                        outline="#00e5ff")
canvas.create_text(x + 260, y + 124, text="{label}", fill="#eaf6ff",
                   font=("Segoe UI", 11, "bold"))

root.after({ms}, root.destroy)
root.mainloop()
"""


def show_arrow(x: int, y: int, label: str = "here", ms: int = ARROW_MS):
    """Best effort: a missing overlay must never stop the action itself."""

    try:

        import subprocess
        import sys

        label = re.sub(r"[^ -~]", "", (label or "here"))[:34].replace('"', "")

        script = ARROW_SCRIPT.format(
            x=int(x), y=int(y), w=3840, h=2160, ms=int(ms), label=label
        )

        subprocess.Popen(
            [sys.executable, "-c", script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    except Exception as error:

        logger.info("Arrow overlay skipped: %s", error)


# -------------------------------------------------------------------- agent


def _extract_json(text: str):
    """The first JSON object inside a model reply, or None."""

    if not text:
        return None

    text = text.strip()

    if text.startswith("```"):

        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)

        text = re.sub(r"```$", "", text).strip()

    try:
        return json.loads(text)

    except ValueError:
        pass

    start = text.find("{")

    while start != -1:

        depth = 0

        for index in range(start, len(text)):

            if text[index] == "{":
                depth += 1

            elif text[index] == "}":

                depth -= 1

                if depth == 0:

                    try:
                        return json.loads(text[start:index + 1])

                    except ValueError:
                        break

        start = text.find("{", start + 1)

    return None


def _act(step: dict, dry_run: bool) -> dict:
    """Carry out one planned step; dry_run only reports what would happen."""

    action = str(step.get("action") or "").lower()

    if action == "click":

        x = int(step.get("x") or 0)
        y = int(step.get("y") or 0)

        if dry_run:
            return {"action": "click", "x": x, "y": y, "dry_run": True}

        click(x, y)

        return {"action": "click", "x": x, "y": y}

    if action == "type" and step.get("text"):

        text = str(step["text"])

        return {"action": "type", "text": text, "dry_run": dry_run} if dry_run else type_text(text)

    if action == "press" and step.get("text"):

        key = str(step["text"])

        return {"action": "press", "key": key, "dry_run": dry_run} if dry_run else press(key)

    if action == "scroll":

        amount = int(step.get("amount") or 3)

        return (
            {"action": "scroll", "amount": amount, "dry_run": True}
            if dry_run
            else scroll(amount)
        )

    if action == "open_url" and step.get("text"):

        url = str(step["text"]).strip()

        return (
            {"action": "open_url", "url": url, "dry_run": True}
            if dry_run
            else open_url(url)
        )

    return {"action": action or "none", "dry_run": dry_run}


def run_task(goal: str, max_steps: int = MAX_STEPS, dry_run: bool = False) -> dict:
    """Look at the screen, act, look again — until the goal is done."""

    provider = screen_reader.ZaiProvider()

    if not provider.health():

        return {"success": False, "error": "ZAI_API_KEY is not set."}

    history = []
    steps = []
    answer = ""

    for index in range(1, max_steps + 1):

        shot = screen_reader.screenshot.capture_screen("agent")

        if not shot.get("success"):

            return {"success": False, "error": shot.get("error") or "Screen capture failed."}

        image = screen_reader.shrink(shot["path"])

        prompt = PROMPT.format(
            goal=goal,
            step=index,
            max_steps=max_steps,
            history="\n".join(history) or "(none)",
        )

        reply = provider.see(prompt, str(image))

        if not reply.get("success"):

            error = str(reply.get("error") or "The vision model did not answer.")

            text = error.lower()

            if any(word in text for word in ("insufficient", "balance", "recharge", "402", "429")):

                error = (
                    "The z.ai account has no balance for the vision model. "
                    "Recharge z.ai and ask again."
                )

            return {
                "success": False,
                "error": error,
                "steps": steps,
                "path": shot["path"],
            }

        plan = _extract_json(reply.get("answer", ""))

        if plan is None:

            return {
                "success": False,
                "error": "The screen agent could not read a plan from the screen.",
                "steps": steps,
                "path": shot["path"],
                "raw": (reply.get("answer") or "")[:400],
            }

        action = str(plan.get("action") or "").lower()
        thought = str(plan.get("thought") or "").strip()

        if action == "answer" or action == "done":

            if plan.get("text"):
                answer = str(plan["text"]).strip()

            elif thought:
                answer = thought

            steps.append(
                {"step": index, "thought": thought, "action": action, "done": True}
            )

            return {
                "success": True,
                "goal": goal,
                "answer": answer,
                "steps": steps,
                "finished": True,
                "path": shot["path"],
            }

        if action == "click" and plan.get("x") is not None:

            show_arrow(int(plan.get("x") or 0), int(plan.get("y") or 0), thought)

            time.sleep(min(0.9, ARROW_MS / 1000))

        done = _act(plan, dry_run)

        steps.append(
            {
                "step": index,
                "thought": thought,
                "action": action,
                "detail": done,
                "done": False,
            }
        )

        history.append(f"{index}. {thought} ({action})")

        time.sleep(0.6)

    return {
        "success": True,
        "goal": goal,
        "answer": "Itni steps me kaam poora nahi hua. Bolo to aage badhau.",
        "steps": steps,
        "finished": False,
    }


def narrate(result: dict) -> str:
    """The step-by-step reply, in plain sentences."""

    steps = result.get("steps") or []

    if not steps:
        return result.get("answer") or ""

    lines = []

    for item in steps:

        thought = (item.get("thought") or "").strip()

        action = item.get("action")

        what = {
            "click": "click kiya",
            "type": "type kiya",
            "press": "key dabayi",
            "scroll": "scroll kiya",
            "open_url": "page khola",
            "answer": "padh liya",
            "done": "kaam poora",
        }.get(action, action or "")

        lines.append(
            f"{item.get('step')}. {thought} — {what}" if thought else f"{item.get('step')}. {what}"
        )

    answer = (result.get("answer") or "").strip()

    if answer:
        lines.append("")
        lines.append(answer)

    return "\n".join(lines)
