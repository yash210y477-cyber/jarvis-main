"""Morning briefing, assembled locally from the clock, stats and memory."""

import psutil

from brain import local_clock


def _greeting(moment) -> str:

    hour = moment.hour

    if hour < 5:

        return "Still up"

    if hour < 12:

        return "Good morning"

    if hour < 17:

        return "Good afternoon"

    if hour < 21:

        return "Good evening"

    return "Good night"


def _stats() -> str:

    cpu = round(psutil.cpu_percent(interval=0.2))

    ram = round(psutil.virtual_memory().percent)

    try:

        disk = psutil.disk_usage("C:\\")

    except OSError:

        disk = psutil.disk_usage("/")

    text = f"CPU {cpu}%, RAM {ram}%, storage {round(disk.percent)}%"

    battery = psutil.sensors_battery()

    if battery:

        state = "plugged in" if battery.power_plugged else "on battery"

        text += f", battery {round(battery.percent)}% ({state})"

    return text


def build_briefing(memory=None, reminders=None) -> str:

    moment = local_clock.now()

    name = ""

    facts = []

    if memory is not None:

        try:

            name = (memory.get_profile() or {}).get("name") or ""

            facts = [
                f"{item.get('key')}: {item.get('value')}"
                for item in (memory.all_facts() or [])
                if item.get("key") and item.get("value")
            ][:5]

        except Exception:

            facts = []

    lines = [
        f"{_greeting(moment)}{(', ' + name) if name else ''}.",
        (
            f"Today is {moment.strftime('%A, %d %B %Y')}, "
            f"{moment.strftime('%I:%M %p').lstrip('0')}."
        ),
        _stats(),
    ]

    if reminders:

        upcoming = []

        for item in reminders[:5]:

            remaining = int(item.get("remaining") or 0)

            minutes = max(1, remaining // 60)

            upcoming.append(f"{item.get('text')} in {minutes} min")

        lines.append("Reminders: " + "; ".join(upcoming))

    else:

        lines.append("No reminders waiting.")

    if facts:

        lines.append("I remember: " + ", ".join(facts))

    return "\n".join(lines)
