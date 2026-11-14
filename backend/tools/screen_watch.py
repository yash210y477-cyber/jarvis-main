"""Watch the screen continuously and explain what is happening.

Two things are noticed without any command:

- the page changes (a big visual difference that then settles), so a newly opened
  site or article gets explained, and
- the cursor stops on one spot for a moment, which is how a person "points" at
  something, so that button, image or word gets explained instead.

The loop is deliberately cheap: a small greyscale frame every few seconds, one
vision request only when something is actually new, and a cooldown so a busy
screen cannot turn into a stream of interruptions.
"""

import ctypes
import ctypes.wintypes
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageChops, ImageStat

from config.settings import settings

logger = logging.getLogger(__name__)

BACKEND = Path(__file__).resolve().parents[1]

FRAME_DIR = BACKEND / "data" / "screen_watch"

SMALL = (320, 180)

PAGE_QUESTION = (
    "The user just opened or changed this page. Say in 2 short sentences what "
    "this page is about and what they can do here. No preamble."
)

CURSOR_QUESTION = (
    "The user is pointing at the highlighted area of their screen. Say in one or "
    "two short sentences what that thing is and what it does."
)


def _cursor_position():
    point = ctypes.wintypes.POINT()

    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))

    return point.x, point.y


class ScreenWatcher:

    def __init__(self, interval=None, cooldown=None, page_diff=None):

        self.interval = interval or int(getattr(settings, "SCREEN_WATCH_INTERVAL", 8))

        self.cooldown = cooldown or int(getattr(settings, "SCREEN_WATCH_COOLDOWN", 25))

        self.page_diff = page_diff or float(
            getattr(settings, "SCREEN_WATCH_PAGE_DIFF", 18)
        )

        self.dwell = float(getattr(settings, "SCREEN_WATCH_DWELL", 1.6))

        self.crop = int(getattr(settings, "SCREEN_WATCH_CROP", 420))

        self.speak_enabled = str(getattr(settings, "SCREEN_WATCH_SPEAK", "1")) not in (
            "0", "false", "no"
        )

        self.thread = None
        self.running = False

        self.lock = threading.Lock()

        self.events = []
        self.next_id = 1

        self.error = ""
        self.last_kind = ""
        self.frames = 0

    # ------------------------------------------------------------- lifecycle

    def start(self) -> dict:

        if self.running:

            return {"success": True, "watching": True, "message": "Already watching."}

        from providers.zai import ZaiProvider

        provider = ZaiProvider()

        if not provider.health():

            self.error = "ZAI_API_KEY is not set."

            return {"success": False, "watching": False, "error": self.error}

        self.error = ""
        self.running = True

        self.thread = threading.Thread(target=self._loop, daemon=True)

        self.thread.start()

        return {"success": True, "watching": True, "message": "Watching your screen."}

    def stop(self) -> dict:

        self.running = False

        return {
            "success": True,
            "watching": False,
            "message": "Stopped watching the screen.",
            "events": len(self.events),
        }

    def status(self) -> dict:

        return {
            "watching": self.running,
            "frames": self.frames,
            "events": len(self.events),
            "error": self.error,
            "last_kind": self.last_kind,
            "interval": self.interval,
            "speak": self.speak_enabled,
        }

    def since(self, event_id: int = 0) -> list:

        with self.lock:

            return [event for event in self.events if event["id"] > event_id]

    # ----------------------------------------------------------------- loop

    def _grab(self):
        """One small greyscale frame of the primary screen."""

        from PIL import ImageGrab

        image = ImageGrab.grab(all_screens=False)

        return image, image.convert("L").resize(SMALL)

    def _loop(self):

        previous = None
        pending = None
        last_event = 0.0
        cursor = (0, 0)
        cursor_since = time.time()
        pointed = None

        while self.running:

            try:

                image, small = self._grab()

                self.frames += 1

                difference = 0.0

                if previous is not None:

                    difference = ImageStat.Stat(ImageChops.difference(previous, small)).mean[0]

                previous = small

                now = time.time()

                position = _cursor_position()

                if abs(position[0] - cursor[0]) > 8 or abs(position[1] - cursor[1]) > 8:

                    cursor = position
                    cursor_since = now
                    pointed = None

                # A page change: big difference, and it stays different next frame.
                if difference >= self.page_diff and now - last_event > self.cooldown:

                    if pending is None:

                        pending = now

                    elif now - pending > self.interval * 0.8:

                        if self._explain_page(image):

                            last_event = now

                        pending = None

                elif difference < self.page_diff:

                    pending = None

                # A point: the cursor has been sitting still for a moment.
                if (
                    now - cursor_since >= self.dwell
                    and now - last_event > self.cooldown
                    and pointed != position
                ):

                    pointed = position

                    if self._explain_cursor(image, position):

                        last_event = now

            except Exception as error:

                logger.info("Screen watch loop: %s", error)

                self.error = str(error)[:200]

            time.sleep(self.interval)

    # --------------------------------------------------------------- explain

    def _save(self, image, kind: str) -> Path:

        FRAME_DIR.mkdir(parents=True, exist_ok=True)

        path = FRAME_DIR / f"{kind}-{datetime.now():%Y%m%d-%H%M%S}.jpg"

        picture = image

        if picture.width > 1400:

            ratio = 1400 / picture.width

            picture = picture.resize((1400, int(picture.height * ratio)), Image.LANCZOS)

        picture.convert("RGB").save(path, format="JPEG", quality=82)

        return path

    def _ask(self, question: str, path: Path):

        from providers.zai import ZaiProvider

        reply = ZaiProvider().see(question, str(path))

        if not reply.get("success"):

            self.error = str(reply.get("error"))[:200]

            text = self.error.lower()

            # No balance or no key will not fix itself: stop instead of asking again.
            if any(
                word in text
                for word in ("insufficient", "balance", "recharge", "401", "402", "429")
            ):

                self.running = False

                self.error = (
                    "Screen watch stopped: the z.ai vision model has no balance. "
                    "Recharge z.ai, then say \"watch my screen\" again."
                )

            return ""

        return (reply.get("answer") or "").strip()

    def _publish(self, kind: str, text: str, image_path: Path):

        with self.lock:

            event = {
                "id": self.next_id,
                "time": datetime.now().strftime("%H:%M:%S"),
                "kind": kind,
                "text": text,
                "image": str(image_path),
            }

            self.next_id += 1

            self.events.append(event)

            self.events = self.events[-40:]

        self.last_kind = kind

        self._announce(text)

        return event

    def _announce(self, text: str):

        if not text:

            return

        try:

            from notify.toast import notify

            notify("JARVIS", text[:200], "JARVIS")

        except Exception as error:

            logger.info("Screen watch toast skipped: %s", error)

        if not self.speak_enabled:

            return

        try:

            self._speak_windows(text)

        except Exception as error:

            logger.info("Screen watch speech skipped: %s", error)

    def _speak_windows(self, text: str):

        """Windows SAPI: instant, no download, and it never blocks the loop."""

        import subprocess

        safe = text.replace("'", " ").replace('"', " ")[:300]

        script = (
            "Add-Type -AssemblyName System.Speech;"
            "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
            f"$s.Speak('{safe}')"
        )

        subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    def _explain_page(self, image) -> bool:

        path = self._save(image, "page")

        text = self._ask(PAGE_QUESTION, path)

        if not text:

            return False

        self._publish("page", text, path)

        return True

    def _explain_cursor(self, image, position) -> bool:

        half = self.crop // 2

        left = max(0, position[0] - half)
        top = max(0, position[1] - half)

        box = (left, top, left + self.crop, top + self.crop)

        area = image.crop(box)

        area = area.resize((area.width * 2, area.height * 2), Image.LANCZOS)

        path = self._save(area, "cursor")

        text = self._ask(CURSOR_QUESTION, path)

        if not text:

            return False

        self._publish("cursor", text, path)

        return True


WATCHER = ScreenWatcher()


def start() -> dict:
    return WATCHER.start()


def stop() -> dict:
    return WATCHER.stop()


def status() -> dict:
    return WATCHER.status()


def events(since: int = 0) -> list:
    return WATCHER.since(since)
