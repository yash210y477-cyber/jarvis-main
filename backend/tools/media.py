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



def _endpoint_volume():
    """Windows endpoint volume through pycaw, when it is installed."""

    from pycaw.pycaw import AudioUtilities

    device = AudioUtilities.GetSpeakers()

    volume = getattr(device, "EndpointVolume", None)

    if volume is not None:
        return volume

    # Older pycaw builds only expose Activate().
    from ctypes import POINTER, cast

    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import IAudioEndpointVolume

    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)

    return cast(interface, POINTER(IAudioEndpointVolume))


def get_volume(**_) -> dict:

    try:

        volume = _endpoint_volume()

        percent = round(volume.GetMasterVolumeLevelScalar() * 100)

    except Exception as error:

        return {
            "success": False,
            "error": f"Reading the exact volume needs pycaw: {error}",
        }

    return {
        "success": True,
        "action": "get_volume",
        "volume": percent,
        "message": f"Volume is at {percent}%.",
    }


def set_volume(percent=50, **_) -> dict:

    try:

        percent = max(0, min(100, int(percent)))

    except (TypeError, ValueError):

        return {"success": False, "error": "Give me a volume between 0 and 100."}

    try:

        volume = _endpoint_volume()

        volume.SetMasterVolumeLevelScalar(percent / 100.0, None)

        actual = round(volume.GetMasterVolumeLevelScalar() * 100)

    except Exception:

        # Fallback: walk to zero, then up to the requested level.
        _press(KEYS["volume_down"], 50)

        if percent > 0:
            _press(KEYS["volume_up"], max(1, round(percent / 2)))

        return {
            "success": True,
            "action": "set_volume",
            "volume": percent,
            "approximate": True,
            "message": f"Volume moved to about {percent}%.",
        }

    return {
        "success": True,
        "action": "set_volume",
        "volume": actual,
        "message": f"Volume set to {actual}%.",
    }
