"""Local reminders, alarms and the morning briefing.

Everything runs in-process on this machine: no cloud, no API key. APScheduler
is used when it is installed, otherwise a small thread loop takes over.
"""

import datetime
import json
import re
import threading
import time
import uuid
from pathlib import Path

from notify.toast import notify


try:

    from apscheduler.schedulers.background import BackgroundScheduler

except Exception:

    BackgroundScheduler = None


NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "ninety": 90,
}


def _number(text: str):
    """First number in the text, digits or words."""

    match = re.search(r"\d+", text)

    if match:

        return int(match.group(0))

    for word, value in NUMBER_WORDS.items():

        if re.search(rf"\b{word}\b", text):

            return value

    return None


def parse_when(when, now=None):
    """Turn "in 10 minutes" / "at 7:30 pm" / "tomorrow 9" into a datetime."""

    if isinstance(when, datetime.datetime):

        return when

    if isinstance(when, (int, float)):

        return (now or datetime.datetime.now()) + datetime.timedelta(seconds=float(when))

    text = (when or "").strip().lower()

    if not text:

        return None

    base = now or datetime.datetime.now()

    # -----------------------------
    # Relative: in / after <n> <unit>
    # -----------------------------

    if (
        re.search(r"\b(in|after|baad)\b", text)
        or re.fullmatch(r"\s*\d+\s*", text)
        or re.fullmatch(
            r"\s*\d+\s*(second|seconds|sec|secs|minute|minutes|min|mins|hour|hours|hr|hrs)\s*",
            text,
        )
    ):

        amount = _number(text) or 0

        if amount:

            if re.search(r"\b(hour|hours|ghanta|ghante)\b", text):
                return base + datetime.timedelta(hours=amount)

            if re.search(r"\b(second|seconds|sec|secs)\b", text):
                return base + datetime.timedelta(seconds=amount)

            return base + datetime.timedelta(minutes=amount)

        return None

    # -----------------------------
    # Absolute: [tomorrow] at 7:30 pm
    # -----------------------------

    words = text.replace("at ", " ").replace("baje", "")

    match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m|p\.m)?", words)

    if not match:

        return None

    hour = int(match.group(1))

    minute = int(match.group(2) or 0)

    meridiem = (match.group(3) or "").replace(".", "")

    if meridiem == "pm" and hour < 12:

        hour += 12

    if meridiem == "am" and hour == 12:

        hour = 0

    if not meridiem and hour < 8:

        # "at 7" almost always means evening for alarms.
        hour += 12

    target = base.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if "tomorrow" in text or "kal" in text:

        target += datetime.timedelta(days=1)

    elif target <= base:

        target += datetime.timedelta(days=1)

    return target


class ReminderScheduler:

    def __init__(self, path=None):

        from memory.storage import data_dir

        self.path = Path(path) if path else data_dir() / "reminders.json"

        self.reminders = []

        self.lock = threading.Lock()

        self.memory = None

        self.briefing_at = None

        self.last_briefing = None

        self.scheduler = None

        self.thread = None

        self.stop_event = threading.Event()

        self.load()

    # -----------------------------
    # STORAGE
    # -----------------------------

    def load(self):

        if not self.path.exists():

            return

        try:

            data = json.loads(self.path.read_text(encoding="utf-8"))

        except Exception:

            return

        self.reminders = [
            item for item in data.get("reminders", [])
            if isinstance(item, dict) and item.get("due")
        ]

    def save(self):

        try:

            self.path.parent.mkdir(parents=True, exist_ok=True)

            self.path.write_text(
                json.dumps({"reminders": self.reminders}, indent=2),
                encoding="utf-8",
            )

        except Exception:

            pass

    # -----------------------------
    # LIFECYCLE
    # -----------------------------

    def start(self, memory=None, briefing_hour=None, briefing_minute=None):

        self.memory = memory

        if briefing_hour is not None:

            self.briefing_at = (int(briefing_hour), int(briefing_minute or 0))

        if self.scheduler or (self.thread and self.thread.is_alive()):

            return self.status()

        if BackgroundScheduler:

            self.scheduler = BackgroundScheduler()

            self.scheduler.start()

            for item in list(self.reminders):

                self._schedule(item)

            if self.briefing_at:

                hour, minute = self.briefing_at

                self.scheduler.add_job(
                    self._run_briefing,
                    "cron",
                    hour=hour,
                    minute=minute,
                    id="morning-briefing",
                    replace_existing=True,
                )

        else:

            self.stop_event.clear()

            self.thread = threading.Thread(target=self._loop, daemon=True)

            self.thread.start()

        return self.status()

    def stop(self):

        if self.scheduler:

            try:

                self.scheduler.shutdown(wait=False)

            except Exception:

                pass

            self.scheduler = None

        self.stop_event.set()

        self.thread = None

    def status(self):

        return {
            "engine": "apscheduler" if self.scheduler else "thread",
            "running": bool(self.scheduler) or bool(self.thread and self.thread.is_alive()),
            "briefing_at": self.briefing_at,
            "briefing_last": self.last_briefing,
            "count": len(self.reminders),
        }

    # -----------------------------
    # ADD / LIST / CANCEL
    # -----------------------------

    def add(self, text, when="", seconds=None):

        if seconds:

            due = datetime.datetime.now() + datetime.timedelta(seconds=float(seconds))

        else:

            due = parse_when(when)

        if due is None:

            return {
                "success": False,
                "error": "Tell me when, like \"in 10 minutes\" or \"at 7:30 am\".",
            }

        item = {
            "id": uuid.uuid4().hex[:8],
            "text": (text or "reminder").strip(),
            "due": due.isoformat(timespec="seconds"),
            "created": datetime.datetime.now().isoformat(timespec="seconds"),
        }

        with self.lock:

            self.reminders.append(item)

            self.save()

        self._schedule(item)

        remaining = max(0, int((due - datetime.datetime.now()).total_seconds()))

        return {
            "success": True,
            "reminder": item,
            "in_seconds": remaining,
            "message": (
                f"Reminder set for {due.strftime('%I:%M %p').lstrip('0')} "
                f"({'tomorrow' if due.date() > datetime.date.today() else 'today'}): "
                f"{item['text']}."
            ),
        }

    def _schedule(self, item):

        if not self.scheduler:

            return

        due = datetime.datetime.fromisoformat(item["due"])

        try:

            self.scheduler.add_job(
                self._fire,
                "date",
                run_date=due,
                args=[item["id"]],
                id=item["id"],
                replace_existing=True,
                misfire_grace_time=3600,
            )

        except Exception:

            pass

    def list(self):

        items = []

        for item in sorted(self.reminders, key=lambda entry: entry["due"]):

            try:

                due = datetime.datetime.fromisoformat(item["due"])

            except ValueError:

                continue

            items.append({
                "id": item["id"],
                "text": item["text"],
                "due": item["due"],
                "remaining": max(0, int((due - datetime.datetime.now()).total_seconds())),
            })

        return items

    def cancel(self, reminder_id=""):

        with self.lock:

            if not reminder_id:

                if not self.reminders:

                    return {"success": False, "error": "No reminders to cancel."}

                removed = self.reminders.pop()

            else:

                removed = None

                for item in list(self.reminders):

                    if item["id"] == reminder_id:

                        removed = item

                        self.reminders.remove(item)

                        break

                if removed is None:

                    return {"success": False, "error": "No reminder with that id."}

            self.save()

        if self.scheduler:

            try:

                self.scheduler.remove_job(removed["id"])

            except Exception:

                pass

        return {
            "success": True,
            "reminder": removed,
            "message": f"Cancelled the reminder: {removed['text']}.",
        }

    def clear(self):

        with self.lock:

            self.reminders = []

            self.save()

        return {"success": True, "message": "All reminders cleared."}

    # -----------------------------
    # FIRING
    # -----------------------------

    def _fire(self, reminder_id):

        with self.lock:

            item = next(
                (entry for entry in self.reminders if entry["id"] == reminder_id),
                None,
            )

            if item:

                self.reminders.remove(item)

                self.save()

        if not item:

            return None

        notify("JARVIS reminder", item["text"])

        return item

    def _run_briefing(self):

        from reminders.briefing import build_briefing

        text = build_briefing(self.memory, self.list())

        self.last_briefing = text

        notify("Good morning", text)

        return text

    def briefing(self):

        from reminders.briefing import build_briefing

        return build_briefing(self.memory, self.list())

    # -----------------------------
    # THREAD FALLBACK
    # -----------------------------

    def _loop(self):

        while not self.stop_event.wait(5):

            now = datetime.datetime.now()

            due = []

            with self.lock:

                for item in list(self.reminders):

                    try:

                        when = datetime.datetime.fromisoformat(item["due"])

                    except ValueError:

                        continue

                    if when <= now:

                        due.append(item)

                        self.reminders.remove(item)

                if due:

                    self.save()

            for item in due:

                notify("JARVIS reminder", item["text"])

            if self.briefing_at and not self.stop_event.is_set():

                hour, minute = self.briefing_at

                if (
                    now.hour == hour
                    and now.minute == minute
                    and self.last_briefing is None
                ):

                    self._run_briefing()


SCHEDULER = ReminderScheduler()
