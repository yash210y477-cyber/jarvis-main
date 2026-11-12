"""Speak text aloud with the built-in Windows voice (SAPI).

No extra package is needed: comtypes ships with pycaw and SAPI is part of
Windows. Reminders use this so JARVIS says the reminder itself instead of only
playing a notification beep.
"""

import logging
import threading


log = logging.getLogger("jarvis.speech")

_lock = threading.Lock()

_RATE = 0


def speak(text: str) -> dict:

    message = (text or "").strip()

    if not message:

        return {"success": False, "error": "Nothing to say."}

    try:

        import comtypes
        import comtypes.client

        with _lock:

            comtypes.CoInitialize()

            voice = comtypes.client.CreateObject("SAPI.SpVoice")

            voice.Rate = _RATE

            voice.Speak(message)

        return {"success": True, "spoken": message}

    except Exception as error:

        log.warning("Speaking failed: %s", error)

        return {"success": False, "error": str(error), "spoken": message}


def speak_async(text: str):

    """Speak in the background so callers (scheduler, API) never block."""

    thread = threading.Thread(target=speak, args=(text,), daemon=True)

    thread.start()

    return thread
