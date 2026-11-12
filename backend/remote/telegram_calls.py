"""Bridge Telegram private voice calls to JARVIS.

Phase A: JARVIS answers an incoming private call and plays a spoken greeting, so
the whole call path is proven. Speech-to-text and text-to-speech come next.
"""

import asyncio
import datetime
import logging
import math
import struct
import threading
import time
import wave
from pathlib import Path

from config.settings import settings
from remote.telegram_user import TelegramUserSession


log = logging.getLogger("jarvis.calls")

GREETING_TEXT = "Hello, JARVIS here. How can I help you today?"

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

GREETING_PATH = DATA_DIR / "telegram_greeting.wav"


def _write_tone(path: Path, seconds: float = 0.6, freq: int = 660,
                rate: int = 16000) -> None:
    """A soft tone, used when Windows speech is unavailable."""

    total = int(rate * seconds)

    frames = bytearray()

    for index in range(total):

        envelope = 1 - (index / total)

        value = int(8000 * math.sin(2 * math.pi * freq * index / rate) * envelope)

        frames += struct.pack("<h", value)

    with wave.open(str(path), "wb") as handle:

        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))


def greeting_file() -> Path:
    """Spoken greeting clip, generated once with Windows SAPI."""

    configured = (settings.TELEGRAM_CALL_GREETING or "").strip()

    if configured:

        path = Path(configured)

        if path.exists():
            return path

    if GREETING_PATH.exists() and GREETING_PATH.stat().st_size > 44:

        return GREETING_PATH

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    try:

        import comtypes.client

        stream = comtypes.client.CreateObject("SAPI.SpFileStream")

        stream.Open(str(GREETING_PATH), 3, False)

        voice = comtypes.client.CreateObject("SAPI.SpVoice")

        voice.AudioOutputStream = stream

        voice.Speak(GREETING_TEXT)

        stream.Close()

    except Exception as error:

        log.warning("Speech greeting failed (%s), writing a tone", error)

        _write_tone(GREETING_PATH)

    return GREETING_PATH


class TelegramCallBridge:

    def __init__(self, session: TelegramUserSession = None):

        self.session = session or TelegramUserSession()

        self.client = None
        self.calls = None
        self.loop = None
        self.thread = None
        self.stopper = None

        self.running = False
        self.last_error = ""
        self.last_call = {}
        self.answered = 0

    # ---------------------------------------------------------------- state

    def available(self) -> bool:

        try:

            import pytgcalls  # noqa: F401

            return True

        except Exception as error:

            self.last_error = f"py-tgcalls is not installed: {error}"

            return False

    def enabled(self) -> bool:

        return self.session.configured() and bool(self.session.session_string())

    def status(self) -> dict:

        return {
            "enabled": self.enabled(),
            "running": self.running,
            "session": bool(self.session.session_string()),
            "configured": self.session.configured(),
            "auto_answer": settings.TELEGRAM_CALL_AUTO_ANSWER,
            "allowed": settings.TELEGRAM_CALL_ALLOWED,
            "answered": self.answered,
            "last_call": self.last_call,
            "last_error": self.last_error,
        }

    # ------------------------------------------------------------ lifecycle

    def start(self) -> dict:

        if self.running:

            return self.status()

        if not self.session.configured():

            self.last_error = (
                "Set TELEGRAM_API_ID and TELEGRAM_API_HASH (my.telegram.org), "
                "then log in with /telegram-call/login/start."
            )

            return self.status()

        if not self.session.session_string():

            self.last_error = "No Telegram session yet; run the login flow first."

            return self.status()

        if not self.available():

            return self.status()

        self.last_error = ""
        self.thread = threading.Thread(
            target=self._thread_main, name="jarvis-telegram-calls", daemon=True
        )
        self.thread.start()

        for _ in range(120):

            if self.running or self.last_error:
                break

            time.sleep(0.1)

        return self.status()

    def _thread_main(self) -> None:

        try:

            asyncio.run(self._serve())

        except Exception as error:

            self.last_error = str(error)
            self.running = False

    async def _serve(self) -> None:

        from pytgcalls import PyTgCalls, filters

        from pytgcalls.types import ChatUpdate

        self.loop = asyncio.get_running_loop()

        client = self.session.build()

        await client.connect()

        if not await client.is_user_authorized():

            self.last_error = (
                "The saved Telegram session is no longer authorised; log in again."
            )

            await client.disconnect()

            return

        self.client = client

        self.calls = PyTgCalls(client)

        await self.calls.start()

        self.calls.add_handler(
            self._on_incoming,
            filters.chat_update(ChatUpdate.Status.INCOMING_CALL),
        )

        self.stopper = asyncio.Event()

        self.running = True

        try:

            await self.stopper.wait()

        finally:

            self.running = False

            try:

                await client.disconnect()

            except Exception:

                pass

    def stop(self) -> dict:

        if self.loop is not None and self.stopper is not None:

            try:

                self.loop.call_soon_threadsafe(self.stopper.set)

            except Exception:

                pass

        if self.thread is not None:

            self.thread.join(timeout=5)

        self.thread = None
        self.client = None
        self.calls = None
        self.running = False

        return self.status()

    # ---------------------------------------------------------------- calls

    async def _on_incoming(self, _client, update) -> None:

        chat_id = getattr(update, "chat_id", None)

        entry = {
            "chat_id": chat_id,
            "at": datetime.datetime.now().isoformat(timespec="seconds"),
            "status": "ringing",
        }

        self.last_call = entry

        allowed = settings.TELEGRAM_CALL_ALLOWED

        if allowed and str(chat_id) not in allowed:

            entry["status"] = "rejected"

            try:

                await self.calls.leave_call(chat_id)

            except Exception:

                pass

            return

        if not settings.TELEGRAM_CALL_AUTO_ANSWER:

            return

        try:

            await self.calls.play(chat_id, greeting_file())

            entry["status"] = "answered"
            self.answered += 1

        except Exception as error:

            entry["status"] = "failed"
            entry["error"] = str(error)
            self.last_error = str(error)

    def _run(self, coro, timeout: float = 30.0):

        if self.loop is None:

            return None

        return asyncio.run_coroutine_threadsafe(coro, self.loop).result(timeout)

    def answer(self, chat_id, seconds: int = 0) -> dict:

        if not self.running:

            return {"success": False, "error": "The call bridge is not running."}

        async def _answer():

            await self.calls.play(chat_id, greeting_file())

            if seconds and seconds > 0:

                await asyncio.sleep(seconds)

            return {"success": True, "chat_id": chat_id, "status": "answered"}

        try:

            return self._run(_answer())

        except Exception as error:

            return {"success": False, "error": str(error)}

    def hangup(self, chat_id) -> dict:

        if not self.running:

            return {"success": False, "error": "The call bridge is not running."}

        async def _hangup():

            await self.calls.leave_call(chat_id)

            return {"success": True, "chat_id": chat_id, "status": "left"}

        try:

            return self._run(_hangup())

        except Exception as error:

            return {"success": False, "error": str(error)}


CALL_BRIDGE = TelegramCallBridge()
