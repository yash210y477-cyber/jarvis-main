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
from remote.call_agent import CallConversation, clip_duration
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

        self.brain = None
        self.conversation = None

    # ---------------------------------------------------------------- state

    def available(self) -> bool:

        # Do not import pytgcalls here: its sync layer binds every call to the
        # event loop that was running when it was first imported. Importing on
        # the caller's thread (FastAPI startup runs on the uvicorn loop) made
        # the bridge schedule its work on the wrong loop afterwards.

        import importlib.util

        if importlib.util.find_spec("pytgcalls") is not None:

            return True

        self.last_error = "py-tgcalls is not installed: pip install py-tgcalls"

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
            "talk": settings.TELEGRAM_CALL_CONVERSATION,
            "conversation": (
                self.conversation.status() if self.conversation else None
            ),
            "last_call": self.last_call,
            "last_error": self.last_error,
        }

    def attach_brain(self, brain) -> None:

        self.brain = brain

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

            log.exception("Telegram call bridge crashed")

            self.last_error = str(error)
            self.running = False

    async def _serve(self) -> None:

        self.loop = asyncio.get_running_loop()

        from pytgcalls import PyTgCalls, filters

        from pytgcalls.types import ChatUpdate, Direction

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

        # Phase B: the caller's audio arrives as stream frames.
        self.calls.add_handler(
            self._on_frames,
            filters.stream_frame(Direction.INCOMING),
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

            if settings.TELEGRAM_CALL_CONVERSATION and self.brain is not None:

                asyncio.create_task(self._start_conversation(chat_id))

        except Exception as error:

            entry["status"] = "failed"
            entry["error"] = str(error)
            self.last_error = str(error)

    async def _on_frames(self, _client, update) -> None:

        conversation = self.conversation

        if conversation is None or conversation.chat_id != update.chat_id:
            return

        payload = b"".join(
            getattr(frame, "data", b"") for frame in update.frames
        )

        for utterance in conversation.feed(payload):

            asyncio.create_task(conversation.handle(utterance))

    async def _start_conversation(self, chat_id) -> None:

        try:

            # Let the greeting finish before listening for an answer.
            await asyncio.sleep(clip_duration(greeting_file()) + 0.4)

            conversation = CallConversation(
                self.calls, brain=self.brain, chat_id=chat_id
            )

            await conversation.start()

            self.conversation = conversation

        except Exception as error:

            self.last_error = str(error)

            log.warning("Starting the call conversation failed: %s", error)

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

    def say(self, text: str, chat_id=None) -> dict:

        conversation = self.conversation

        if conversation is None:

            return {
                "success": False,
                "error": "No call is in a conversation right now.",
            }

        target = chat_id or conversation.chat_id

        async def _say():
            conversation.chat_id = target
            return await conversation.say(text)

        try:
            return self._run(_say(), timeout=120)
        except Exception as error:
            return {"success": False, "error": str(error)}

    def hangup(self, chat_id) -> dict:

        if not self.running:

            return {"success": False, "error": "The call bridge is not running."}

        async def _hangup():

            if (
                self.conversation is not None
                and self.conversation.chat_id == chat_id
            ):
                self.conversation = None

            await self.calls.leave_call(chat_id)

            return {"success": True, "chat_id": chat_id, "status": "left"}

        try:

            return self._run(_hangup())

        except Exception as error:

            return {"success": False, "error": str(error)}


CALL_BRIDGE = TelegramCallBridge()
