"""Type what the user said into whichever window has focus.

Dictation, without a separate editor: the text goes through the clipboard and a
single Ctrl+V, so emoji, newlines and long lines arrive intact. The previous
clipboard content is put back afterwards, so dictation does not steal it.
"""

import ctypes
import logging
import time

from tools import clipboard

logger = logging.getLogger(__name__)


def _paste():

    user32 = ctypes.windll.user32

    user32.keybd_event(0x11, 0, 0, 0)        # ctrl down
    user32.keybd_event(0x56, 0, 0, 0)        # v down
    user32.keybd_event(0x56, 0, 0x0002, 0)   # v up
    user32.keybd_event(0x11, 0, 0x0002, 0)   # ctrl up


def type_here(text: str, restore_clipboard: bool = True) -> dict:
    """Paste text into the focused window."""

    text = (text or "").strip()

    if not text:

        return {"success": False, "error": "There is nothing to type."}

    previous = ""

    if restore_clipboard:

        previous = (clipboard.get_clipboard() or {}).get("content") or ""

    written = clipboard.set_clipboard(text)

    if not written.get("success"):

        return {
            "success": False,
            "error": written.get("error") or "Could not reach the clipboard.",
        }

    time.sleep(0.12)

    _paste()

    time.sleep(0.25)

    if restore_clipboard and previous:

        clipboard.set_clipboard(previous)

    shown = text if len(text) <= 60 else text[:57] + "..."

    return {
        "success": True,
        "action": "type_here",
        "text": text,
        "message": f'Typed "{shown}" where the cursor was.',
    }
