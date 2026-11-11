"""Media and volume control through the Windows media keys."""

import ctypes
import time


user32 = ctypes.windll.user32 if hasattr(ctypes, "windll") else None

KEYEVENTF_KEYUP = 0x0002

KEYS = {
    "play_pause": 0xB3,
    "next": 0xB0,
    "previous": 0xB1,
    "stop": 0xB2,
    "mute": 0xAD,
    "volume_up": 0xAF,
    "volume_down": 0xAE,
}

LABELS = {
    "play_pause": "Toggled play/pause",
    "next": "Skipped to the next track",
    "previous": "Went back a track",
    "stop": "Stopped playback",
    "mute": "Toggled mute",
    "volume_up": "Turned the volume up",
    "volume_down": "Turned the volume down",
}


def _press(vk, times=1):

    for _ in range(max(1, int(times))):

        user32.keybd_event(vk, 0, 0, 0)

        user32.keybd_event(vk, 0, KEYEVENTF_KEYUP, 0)

        time.sleep(0.05)


def control(action: str, steps: int = 1) -> dict:

    if user32 is None:

        return {"success": False, "error": "Media control needs Windows."}

    key = (action or "").strip().lower().replace(" ", "_")

    aliases = {
        "play": "play_pause",
        "pause": "play_pause",
        "toggle": "play_pause",
        "resume": "play_pause",
        "skip": "next",
        "back": "previous",
        "prev": "previous",
        "louder": "volume_up",
        "quieter": "volume_down",
        "unmute": "mute",
        "silence": "mute",
    }

    key = aliases.get(key, key)

    if key not in KEYS:

        return {
            "success": False,
            "error": (
                "Unknown media action. Use one of: "
                + ", ".join(sorted(KEYS))
            ),
        }

    _press(KEYS[key], steps if key in ("volume_up", "volume_down") else 1)

    return {
        "success": True,
        "action": key,
        "message": LABELS[key],
    }
