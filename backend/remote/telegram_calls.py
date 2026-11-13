"""Bridge Telegram private voice calls to JARVIS.

Phase A: JARVIS answers an incoming private call and plays a spoken greeting, so
the whole call path is proven. Speech-to-text and text-to-speech come next.
"""

import asyncio
import datetime
import logging
import math
import os
import shutil
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


def audio_tools_dir() -> str:
    """Find ffmpeg/ffprobe and put them on PATH; pytgcalls needs both."""

    if shutil.which("ffmpeg") and shutil.which("ffprobe"):

        return str(Path(shutil.which("ffmpeg")).parent)

    candidates = []

    local = os.environ.get("LOCALAPPDATA")

    if local:

        packages = Path(local) / "Microsoft" / "WinGet" / "Packages"

        if packages.is_dir():

            candidates.extend(sorted(packages.glob("*/**/bin")))

    candidates.extend([
        Path("C:\ffmpeg\bin"),
        Path("C:\Program Files\ffmpeg\bin"),
        DATA_DIR.parent / "tools" / "ffmpeg" / "bin",
    ])

    for candidate in candidates:

        if (candidate / "ffprobe.exe").is_file() and (
            candidate / "ffmpeg.exe"
        ).is_file():

            os.environ["PATH"] = (
                str(candidate) + os.pathsep + os.environ.get("PATH", "")
            )

            log.info("Using ffmpeg from %s", candidate)

            return str(candidate)

    return ""


async def _every_update(_filter, _client, _update) -> bool:
    """Match every update; pytgcalls calls filters as (self, client, update)."""

    return True


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
        self.messages = 0
        self.updates_seen = 0
        self.frames = 0
        self.frame_bytes = 0
        self.in_call = False
        self.call_chat = None
        self.last_update = ""

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
            "messages": self.messages,
            "updates_seen": self.updates_seen,
            "in_call": self.in_call,
            "frames": self.frames,
            "frame_bytes": self.frame_bytes,
            "last_update": self.last_update,
            "talk": settings.TELEGRAM_CALL_CONVERSATION,
            "conversation": (
                self.conversation.status() if self.conversation else None
            ),
            "last_call": self.last_call,
            "audio_tools": audio_tools_dir(),
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

        # pytgcalls shells out to ffmpeg/ffprobe; make sure they are on PATH
        # before the library looks them up.
        audio_tools_dir()

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

        # Count every update, so /telegram-call/status shows whether a
        # call reaches the bridge at all.
        self.calls.add_handler(
            self._on_any, filters.create(_every_update)
        )

        # Texting this account used to be silent: answer it with the brain.
        from telethon import events

        client.add_event_handler(
            self._on_message, events.NewMessage(incoming=True)
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

    async def _on_any(self, _client, update) -> None:

        self.updates_seen += 1

        self.last_update = f"{type(update).__name__}: {update!r}"[:200]

        log.debug("Telegram call update: %s", self.last_update)

        self._track(update)

    def _track(self, update) -> None:
        """Follow the call state: pytgcalls dials out if play/record runs
        after the call has already ended."""

        status = getattr(update, "status", None)

        chat_id = getattr(update, "chat_id", None)

        if status is None:

            return

        try:

            from pytgcalls.types import ChatUpdate

        except Exception:

            return

        flags = ChatUpdate.Status

        if status & flags.INCOMING_CALL:

            self.in_call = True
            self.call_chat = chat_id

        elif status & flags.LEFT_CALL:

            if self.call_chat is None or chat_id == self.call_chat:

                self.in_call = False
                self.call_chat = None
                self.conversation = None

    def _answer_text(self, text: str) -> str:

        if self.brain is None:

            return "JARVIS is still starting up."

        try:

            result = self.brain.chat(text)

            return (result.get("response") or "Done.")[:4000]

        except Exception as error:

            return f"Something went wrong: {error}"

    async def _on_message(self, event) -> None:
        """Reply to normal text sent to the JARVIS account, like the bot."""

        try:

            if event.out or not event.is_private:

                return

            text = (event.raw_text or "").strip()

            if not text:

                return

            sender = await event.get_sender()

            user_id = getattr(sender, "id", None)

            allowed = settings.TELEGRAM_CALL_ALLOWED

            if allowed and str(user_id) not in allowed:

                log.info("Ignoring message from unlisted user %s", user_id)

                return

            reply = await asyncio.to_thread(self._answer_text, text)

            await event.reply(reply)

            self.messages += 1

        except Exception as error:

            log.warning("Replying on the JARVIS account failed: %s", error)


    async def _on_incoming(self, _client, update) -> None:

        chat_id = getattr(update, "chat_id", None)

        entry = {
            "chat_id": chat_id,
            "at": datetime.datetime.now().isoformat(timespec="seconds"),
            "status": "ringing",
        }

        self.last_call = entry

        self.in_call = True
        self.call_chat = chat_id

        allowed = settings.TELEGRAM_CALL_ALLOWED

        if allowed and str(chat_id) not in allowed:

            entry["status"] = "rejected"

            self.in_call = False
            self.call_chat = None

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

            self.in_call = False
            self.call_chat = None

            # Never leave the caller listening to a silent line.

            try:

                await self.calls.leave_call(chat_id)

            except Exception:

                pass

    async def _on_frames(self, _client, update) -> None:

        conversation = self.conversation

        if conversation is None or conversation.chat_id != update.chat_id:
            return

        if not self.in_call:

            return

        # pytgcalls Frame keeps its PCM in .frame; .data does not exist,
        # so reading it silently yielded empty audio on every call.
        payload = b"".join(
            getattr(frame, "frame", None) or b"" for frame in update.frames
        )

        self.frames += len(update.frames)
        self.frame_bytes += len(payload)

        for utterance in conversation.feed(payload):

            asyncio.create_task(conversation.handle(utterance))

    async def _start_conversation(self, chat_id) -> None:

        try:

            if not self.in_call:

                return

            # Let the greeting finish before listening for an answer.
            await asyncio.sleep(clip_duration(greeting_file()) + 0.4)

            conversation = CallConversation(
                self.calls,
                brain=self.brain,
                chat_id=chat_id,
                is_active=lambda: self.in_call
                and self.call_chat == chat_id,
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

        if not self.in_call:

            return {
                "success": False,
                "error": "No call is ringing; refusing to dial out.",
            }

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

            self.in_call = False
            self.call_chat = None

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
