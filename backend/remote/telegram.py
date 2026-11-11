"""Telegram bridge: talk to JARVIS from your phone.

Long polling only, so no public URL or webhook is needed. The bot token and
allowed chat ids live in settings; when no allowed ids are configured every
chat is answered, otherwise only the listed ones.
"""

import threading
import time

import requests

from config.settings import settings


API = "https://api.telegram.org/bot{token}/{method}"


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

        self.stop_event.clear()

        self.thread = threading.Thread(target=self._loop, daemon=True)

        self.thread.start()

        return self.status()

    def stop(self):

        self.stop_event.set()

        self.thread = None

    def handle(self, chat_id, text: str) -> str:

        if not self.is_allowed(chat_id):

            return "This chat is not authorized for JARVIS."

        if self.brain is None:

            return "JARVIS is still starting up."

        result = self.brain.chat(text)

        return result.get("response") or "Done."

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

                    self._call(
                        "sendMessage",
                        chat_id=chat_id,
                        text=reply[:4000],
                    )

                    self.messages += 1

            except Exception as error:

                self.last_error = str(error)[:300]

                time.sleep(5)


BRIDGE = TelegramBridge()
