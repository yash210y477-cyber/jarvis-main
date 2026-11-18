"""Telegram bridge: talk to JARVIS from your phone.

Long polling only, so no public URL or webhook is needed. The bot token and
allowed chat ids live in settings; when no allowed ids are configured every
chat is answered, otherwise only the listed ones.
"""

import json
import os
import re
import threading
import time
from pathlib import Path
from urllib.parse import unquote

import psutil
import requests

from config.settings import settings


API = "https://api.telegram.org/bot{token}/{method}"

# A tool that writes a file leaves a "[file]name" line in the reply; the chat
# turns it into a Download button, Telegram sends the file itself.
FILE_MARKER = re.compile(r"^\[file\](\S+)\s*$")

MAX_DOCUMENT_BYTES = 49 * 1024 * 1024


def file_marks(text: str) -> tuple[str, list[str]]:
    """Split the reply into what to say and which files to send."""

    body = []
    paths = []

    for line in (text or "").splitlines():

        found = FILE_MARKER.match(line.strip())

        if found:

            paths.append(unquote(found.group(1)))
        else:

            body.append(line)

    return "\n".join(body).strip(), paths

# One poller per bot token: a second JARVIS process makes every reply arrive
# twice and makes Telegram answer "Conflict" to both of them.
LOCK_PATH = Path(__file__).resolve().parents[1] / "data" / "telegram_bot.lock"


class TelegramBridge:

    def __init__(self, brain=None, token=None, chat_ids=None):

        self.brain = brain

        self.token = (
            settings.TELEGRAM_BOT_TOKEN
            if token is None else token
        )

        allowed = (
            settings.TELEGRAM_ALLOWED_CHAT_IDS
            if chat_ids is None else chat_ids
        )

        self.chat_ids = {str(item) for item in (allowed or [])}

        self.offset = 0

        self.messages = 0

        self.last_error = None

        self.thread = None

        self.stop_event = threading.Event()

        self._lock_owned = False

    def enabled(self) -> bool:

        return bool(self.token)

    def is_allowed(self, chat_id) -> bool:

        if not self.chat_ids:

            return True

        return str(chat_id) in self.chat_ids

    def status(self) -> dict:

        return {
            "success": True,
            "enabled": self.enabled(),
            "running": bool(self.thread and self.thread.is_alive()),
            "allowed_chat_ids": sorted(self.chat_ids),
            "messages": self.messages,
            "last_error": self.last_error,
        }

    def start(self, brain=None):

        if brain is not None:

            self.brain = brain

        if not self.enabled():

            self.last_error = "TELEGRAM_BOT_TOKEN is not set."

            return self.status()

        if self.thread and self.thread.is_alive():

            return self.status()

        if not self._acquire_lock():

            return self.status()

        self.stop_event.clear()

        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

        return self.status()

    def stop(self):

        self.stop_event.set()
        self.thread = None

        self._release_lock()

    def handle(self, chat_id, text: str) -> str:

        if not self.is_allowed(chat_id):

            return (
                "This chat is not authorized for JARVIS.\n"
                f"Your chat id: {chat_id}\n"
                "Add it to TELEGRAM_ALLOWED_CHAT_IDS in backend/.env, "
                "then restart JARVIS."
            )

        command = (text or "").strip().lower()

        if command in ("/start", "/help", "start", "help"):

            return self.help_text()

        if command in ("/status", "status"):

            return self.status_text()

        if self.brain is None:

            return "JARVIS is still starting up."

        result = self.brain.chat(text)

        return result.get("response") or "Done."

    def help_text(self) -> str:
        """Bots cannot receive calls, so point at the real call path."""

        return (
            "JARVIS is online.\n"
            "Chat: just send a message, Hinglish works.\n"
            "Call: a Telegram bot cannot make or receive calls, so there is no "
            "call button here. Call the JARVIS user account directly (the "
            "number logged in with TELEGRAM_API_ID) and JARVIS answers by "
            "itself.\n"
            "Commands: /status, /help"
        )

    def status_text(self) -> str:

        try:

            from remote.telegram_calls import CALL_BRIDGE

            calls = CALL_BRIDGE.status()

        except Exception:

            calls = {}

        chat_on = bool(self.thread and self.thread.is_alive())

        answer_state = "ready" if calls.get("running") else "not running"

        return (
            f"Chat: {'on' if chat_on else 'off'}\n"
            f"Calls: {answer_state}\n"
            f"Answered calls: {calls.get('answered', 0)}"
        )

    # ------------------------------------------------------- single instance

    @staticmethod
    def _lock_owner() -> tuple:
        """The pid and start time written in the lock file, 0 when unreadable.

        A bare pid is not enough: Windows reuses pids, so a leftover lock can
        point at some unrelated process and block the bot forever. The start
        time tells the two apart.
        """

        try:

            raw = LOCK_PATH.read_text(encoding="utf-8").strip()

        except OSError:

            return 0, 0.0

        try:

            data = json.loads(raw)

            return int(data.get("pid") or 0), float(data.get("started") or 0)

        except (ValueError, TypeError, AttributeError):

            pass

        try:

            return int(raw or 0), 0.0

        except ValueError:

            return 0, 0.0

    @staticmethod
    def _owner_is_running(pid: int, started: float) -> bool:

        if not pid or not psutil.pid_exists(pid):

            return False

        if not started:

            # Old lock file: a live pid is the best evidence available.
            return True

        try:

            return abs(psutil.Process(pid).create_time() - started) < 2.0

        except Exception:

            return False

    def _acquire_lock(self) -> bool:

        try:

            LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)

            handle = os.open(
                str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY
            )

        except FileExistsError:

            pid, started = self._lock_owner()

            if pid and pid != os.getpid() and self._owner_is_running(pid, started):

                self.last_error = (
                    f"Another JARVIS is already reading this bot (pid {pid}); "
                    "stop it, otherwise every reply arrives twice."
                )

                return False

            try:

                LOCK_PATH.unlink()

            except OSError:

                pass

            try:

                handle = os.open(
                    str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY
                )

            except OSError:

                self.last_error = "Could not create the bot lock file."

                return False

        try:

            stamp = json.dumps({
                "pid": os.getpid(),
                "started": psutil.Process().create_time(),
            })

            os.write(handle, stamp.encode())

        finally:

            os.close(handle)

        self._lock_owned = True

        return True

    def _release_lock(self) -> None:

        if not self._lock_owned:

            return

        self._lock_owned = False

        try:

            LOCK_PATH.unlink()

        except OSError:

            pass

    # ------------------------------------------------------------- transport

    def _call(self, method: str, **payload):

        response = requests.post(
            API.format(token=self.token, method=method),
            json=payload,
            timeout=40,
        )

        data = response.json()

        if not data.get("ok"):

            raise RuntimeError(data.get("description") or "Telegram error")

        return data.get("result")

    def _send_document(self, chat_id, path: str) -> bool:
        """Upload one generated file, if it stays inside the workspace."""

        from tools import files

        try:

            target = files._resolve(path)

        except ValueError:

            return False

        if not target.is_file() or target.stat().st_size > MAX_DOCUMENT_BYTES:

            return False

        try:

            with target.open("rb") as handle:

                response = requests.post(
                    API.format(token=self.token, method="sendDocument"),
                    data={"chat_id": chat_id},
                    files={"document": (target.name, handle)},
                    timeout=120,
                )

            return bool(response.json().get("ok"))

        except Exception as error:

            self.last_error = str(error)[:300]

            return False

    def _loop(self):

        while not self.stop_event.is_set():

            try:

                updates = self._call(
                    "getUpdates",
                    offset=self.offset,
                    timeout=25,
                ) or []

                self.last_error = None

                for update in updates:

                    self.offset = int(update.get("update_id", self.offset)) + 1

                    message = update.get("message") or {}

                    text = (message.get("text") or "").strip()

                    chat_id = (message.get("chat") or {}).get("id")

                    if not text or chat_id is None:

                        continue

                    reply = self.handle(chat_id, text)

                    body, paths = file_marks(reply)

                    if body:

                        self._call(
                            "sendMessage",
                            chat_id=chat_id,
                            text=body[:4000],
                        )

                    for path in paths:

                        self._send_document(chat_id, path)

                    self.messages += 1

            except Exception as error:

                self.last_error = str(error)[:300]

                time.sleep(5)


BRIDGE = TelegramBridge()
