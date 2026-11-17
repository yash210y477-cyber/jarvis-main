"""Calendar events as standard .ics files, so any calendar app can import them.

No cloud account and no API key: an event becomes a file in
``data/agenda/<slug>.ics`` (double-click to add it to Outlook, Google Calendar or
the Windows Calendar app) and a row in ``data/agenda.json`` for listing.
"""

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from memory.storage import data_dir


def _folder() -> Path:

    path = data_dir() / "agenda"

    path.mkdir(parents=True, exist_ok=True)

    return path


def _index() -> Path:

    return data_dir() / "agenda.json"


def _load() -> list:

    path = _index()

    if not path.exists():

        return []

    try:

        data = json.loads(path.read_text(encoding="utf-8"))

    except Exception:

        return []

    items = data.get("events") if isinstance(data, dict) else data

    return [item for item in items or [] if isinstance(item, dict) and item.get("start")]


def _save(items: list) -> None:

    path = _index()

    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(json.dumps({"events": items}, indent=2), encoding="utf-8")


def _slug(title: str) -> str:

    cleaned = re.sub(r"[^a-z0-9]+", "-", (title or "event").lower()).strip("-")

    return (cleaned or "event")[:40]


def _ics_start(moment: datetime) -> str:

    return moment.strftime("%Y%m%dT%H%M%S")


def _ics_text(value: str) -> str:
    """Escape the characters the iCalendar format reserves."""

    return (
        (value or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def add_event(
    title: str,
    when: str,
    duration_minutes: int = 60,
    location: str = "",
) -> dict:
    """Create a calendar event from "tomorrow at 9" or "in 2 hours"."""

    from reminders.scheduler import parse_when

    title = (title or "").strip() or "Event"
    location = (location or "").strip()

    start = parse_when(when)

    if start is None:

        return {
            "success": False,
            "error": "Tell me when, like \"tomorrow at 9\" or \"in 2 hours\".",
        }

    try:

        minutes = max(5, min(24 * 60, int(duration_minutes or 60)))

    except (TypeError, ValueError):

        minutes = 60

    end = start + timedelta(minutes=minutes)
    uid = uuid.uuid4().hex[:10]

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    ics = "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//JARVIS//Agenda//EN",
            "BEGIN:VEVENT",
            f"UID:{uid}@jarvis.local",
            f"DTSTAMP:{stamp}",
            f"DTSTART:{_ics_start(start)}",
            f"DTEND:{_ics_start(end)}",
            f"SUMMARY:{_ics_text(title)}",
            f"LOCATION:{_ics_text(location)}",
            "END:VEVENT",
            "END:VCALENDAR",
            "",
        ]
    )

    path = _folder() / f"{_slug(title)}-{uid}.ics"
    path.write_text(ics, encoding="utf-8")

    item = {
        "id": uid,
        "title": title,
        "start": start.isoformat(timespec="minutes"),
        "duration_minutes": minutes,
        "location": location,
        "file": str(path),
    }

    items = _load()
    items.append(item)
    _save(items)

    spoken = start.strftime("%I:%M %p").lstrip("0")
    day = "tomorrow" if start.date() == datetime.now().date() + timedelta(days=1) else start.strftime("%A")

    return {
        "success": True,
        "event": item,
        "path": str(path),
        "message": f"Added “{title}” on {day} at {spoken}. Calendar file: {path.name}",
    }


def list_events(days: int = 7) -> dict:
    """Upcoming events, soonest first."""

    try:

        days = max(1, min(365, int(days or 7)))

    except (TypeError, ValueError):

        days = 7

    now = datetime.now()
    horizon = now + timedelta(days=days)

    upcoming = []

    for item in _load():

        try:

            start = datetime.fromisoformat(item["start"])

        except ValueError:

            continue

        if start < now - timedelta(hours=1) or start > horizon:

            continue

        upcoming.append({**item, "remaining_minutes": int((start - now).total_seconds() // 60)})

    upcoming.sort(key=lambda entry: entry["start"])

    return {
        "success": True,
        "count": len(upcoming),
        "events": upcoming,
        "message": (
            f"{len(upcoming)} event(s) in the next {days} day(s)."
            if upcoming
            else f"Nothing on the calendar for the next {days} day(s)."
        ),
    }
