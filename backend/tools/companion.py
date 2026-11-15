"""Push-to-talk: hold Ctrl+Alt, speak, let go — JARVIS hears, answers, speaks.

There is no wake word. The keys are watched with GetAsyncKeyState in one cheap
thread, so it works from any app.

Ctrl+Shift+A asks about one part of the screen (drag a box, it explains it).
"""

import ctypes
import logging
import threading
import time

from tools import card, screen_area

logger = logging.getLogger(__name__)

VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_A = 0x41

SAMPLE_RATE = 16000
MAX_SECONDS = 20
POLL = 0.04
MIN_SECONDS = 0.35

_state = {
    "running": False,
    "recording": False,
    "handler": None,
    "speaker": None,
    "events": [],
    "error": "",
}

_thread = None
_lock = threading.Lock()
_worker = None


def configure(handler=None, speaker=None) -> dict:
    """Give the companion a way to think (a chat function) and to speak."""

    if handler is not None:

        _state["handler"] = handler

    if speaker is not None:

        _state["speaker"] = speaker

    return {"success": True, "handler": bool(_state["handler"]), "speaker": bool(_state["speaker"])}


def _down(code: int) -> bool:

    try:

        return bool(ctypes.windll.user32.GetAsyncKeyState(code) & 0x8000)

    except Exception:

        return False


def _note(kind: str, text: str = "") -> None:

    with _lock:

        _state["events"].append({"at": time.time(), "kind": kind, "text": text})

        _state["events"] = _state["events"][-25:]


def _speak(text: str) -> None:

    text = (text or "").strip()

    if not text:


        return

    speaker = _state.get("speaker")

    if speaker is None:


        return

    try:

        speaker.speak(text)

    except Exception as error:

        logger.info("Companion speak failed: %s", error)



def _respond(text: str) -> None:

    handler = _state.get("handler")

    if handler is None:

        _note("error", "No chat handler is attached.")


        return


    try:

        result = handler(text)

    except Exception as error:

        logger.warning("Companion chat failed: %s", error)

        _note("error", str(error))


        return

    reply = (result.get("response") if isinstance(result, dict) else str(result)) or ""

    _note("reply", reply)

    _speak(reply)


def _ask_area(question: str = "") -> None:


    try:

        result = screen_area.ask_area(question)

    except Exception as error:

        logger.warning("Area ask failed: %s", error)


        return

    if not result.get("success"):

        _note("error", result.get("error") or "Area ask failed.")

        _speak(result.get("error") or "")

        return

    answer = result.get("answer") or ""

    _note("reply", answer)

    card.show_card("JARVIS", answer, seconds=30)

    _speak(answer)


def _record_while_held() -> None:

    import numpy as np
    import sounddevice as sd

    frames = []

    finished = threading.Event()

    def callback(indata, _frames, _time, _status):

        if not finished.is_set():

            frames.append(indata.copy())

    try:

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=1024,
            callback=callback,
        )

        stream.start()

    except Exception as error:

        logger.warning("Push-to-talk microphone failed: %s", error)

        _state["recording"] = False

        _note("error", f"Microphone: {error}")


        return

    started = time.time()

    try:

        while _down(VK_CONTROL) and _down(VK_MENU) and time.time() - started < MAX_SECONDS:

            time.sleep(POLL)

    finally:

        finished.set()

        time.sleep(0.12)

        try:

            stream.stop()

            stream.close()

        except Exception:

            pass

    _state["recording"] = False

    seconds = time.time() - started

    if seconds < MIN_SECONDS or not frames:

        _note("ignored", "too short")


        return

    audio = np.concatenate(frames, axis=0).flatten().astype("float32")


    try:

        from voice.stt import shared

        text = shared().transcribe(audio)

    except Exception as error:

        logger.warning("Push-to-talk transcription failed: %s", error)

        _note("error", str(error))


        return

    text = (text or "").strip()

    if not text:

        _note("ignored", "nothing heard")


        return

    _note("heard", text)

    _respond(text)


def _loop() -> None:

    global _worker

    was_held = False
    area_was_down = False

    while _state["running"]:

        held = _down(VK_CONTROL) and _down(VK_MENU) and not _down(VK_SHIFT)

        if held and not was_held and not _state["recording"]:

            _state["recording"] = True


            _worker = threading.Thread(target=_record_while_held, daemon=True)

            _worker.start()

        was_held = held

        area_down = _down(VK_CONTROL) and _down(VK_SHIFT) and _down(VK_A)

        if area_down and not area_was_down:

            threading.Thread(target=_ask_area, daemon=True).start()

        area_was_down = area_down

        time.sleep(POLL)


def start() -> dict:

    global _thread

    if _state["running"]:

        return {"success": True, "message": "Push-to-talk is already on."}

    if not _state.get("handler"):

        return {
            "success": False,
            "error": "Push-to-talk needs the chat handler; start JARVIS first.",
        }

    _state["running"] = True
    _state["error"] = ""



    _thread = threading.Thread(target=_loop, daemon=True, name="jarvis-ptt")

    _thread.start()

    _note("started", "Ctrl+Alt hold to talk")

    return {
        "success": True,
        "message": "Push-to-talk on: hold Ctrl+Alt and speak, Ctrl+Shift+A for a screen area.",
    }


def stop() -> dict:

    _state["running"] = False
    _state["recording"] = False


    _note("stopped", "")

    return {"success": True, "message": "Push-to-talk off."}


def status() -> dict:

    return {
        "success": True,
        "running": _state["running"],
        "recording": _state["recording"],
        "shortcuts": {
            "talk": "hold Ctrl+Alt",
            "area": "Ctrl+Shift+A",
        },
        "events": list(_state["events"])[-10:],
    }


def events() -> dict:

    return {"success": True, "events": list(_state["events"])}


def heard(text: str) -> None:
    """Hook for the API: report a phrase without a microphone."""

    _note("heard", text)
