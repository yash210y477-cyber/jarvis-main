"""Timers and alarms that survive inside the running backend process."""

import threading
import time
import uuid
import winsound


class TimerManager:

    def __init__(self):

        self.lock = threading.Lock()

        self.timers = {}

    def set(self, seconds: int, label: str = ""):

        seconds = int(seconds)

        if seconds <= 0:

            return {"success": False, "error": "Duration must be positive."}

        if seconds > 86400:

            return {"success": False, "error": "Max timer is 24 hours."}

        timer_id = uuid.uuid4().hex[:6]

        label = (label or "").strip() or "timer"

        entry = {
            "id": timer_id,
            "label": label,
            "seconds": seconds,
            "fires_at": time.time() + seconds,
            "cancelled": False,
        }

        handle = threading.Timer(seconds, self._ring, args=(timer_id,))
        handle.daemon = True

        entry["handle"] = handle

        with self.lock:

            self.timers[timer_id] = entry

        handle.start()

        return {
            "success": True,
            "id": timer_id,
            "label": label,
            "seconds": seconds,
            "fires_at": entry["fires_at"],
            "message": f"Timer set for {_human(seconds)} ({label}).",
        }

    def _ring(self, timer_id):

        with self.lock:

            entry = self.timers.pop(timer_id, None)

        if not entry:
            return

        try:

            for _ in range(3):

                winsound.Beep(880, 250)

                time.sleep(0.15)

        except Exception:

            pass

    def cancel(self, timer_id: str = ""):

        with self.lock:

            if timer_id:

                entry = self.timers.pop(timer_id, None)

            else:

                entry = self.timers.pop(next(iter(self.timers), ""), None)

        if not entry:

            return {"success": False, "error": "No matching timer."}

        entry["handle"].cancel()

        return {
            "success": True,
            "id": entry["id"],
            "message": f"Cancelled the {entry['label']} timer.",
        }

    def list(self):

        now = time.time()

        with self.lock:

            active = [
                {
                    "id": entry["id"],
                    "label": entry["label"],
                    "seconds": entry["seconds"],
                    "remaining": round(entry["fires_at"] - now),
                }
                for entry in self.timers.values()
            ]

        return {"success": True, "timers": active, "count": len(active)}


def _human(seconds: int) -> str:

    minutes, secs = divmod(int(seconds), 60)

    hours, minutes = divmod(minutes, 60)

    parts = []

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    if secs or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


TIMERS = TimerManager()
