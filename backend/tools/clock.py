"""Local clock tool: no network, no provider, no API key."""

import datetime
import time

from brain import local_clock


PARTS = (
    "now", "date", "time", "weekday", "day", "month", "year",
    "week", "timezone", "iso",
)


def _fields(moment: datetime.datetime) -> dict:

    return {
        "iso": moment.isoformat(timespec="seconds"),
        "date": moment.strftime("%Y-%m-%d"),
        "time": moment.strftime("%H:%M"),
        "time_12h": moment.strftime("%I:%M %p").lstrip("0"),
        "weekday": moment.strftime("%A"),
        "day": moment.day,
        "month": moment.strftime("%B"),
        "month_number": moment.month,
        "year": moment.year,
        "week": moment.isocalendar().week,
        "timezone": moment.tzname(),
        "timestamp": int(time.time()),
    }


def get_datetime(part="now"):

    requested = (part or "now").strip().lower()

    if requested in ("today",):

        requested = "date"

    if requested in ("month name", "monthname"):

        requested = "month"

    moment = local_clock.now()

    fields = _fields(moment)

    if requested not in PARTS:

        requested = "now"

    if requested == "iso":

        spoken = fields["iso"]

    elif requested == "now":

        spoken = local_clock.render("datetime")

    elif requested == "day":

        spoken = f"Today is the {moment.day}{_suffix(moment.day)}."

    else:

        spoken = local_clock.render(
            "date" if requested == "today" else requested
        )

    return {
        "success": True,
        "part": requested,
        "spoken": spoken,
        **fields,
    }


def _suffix(day: int) -> str:

    if 10 <= day % 100 <= 20:

        return "th"

    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
