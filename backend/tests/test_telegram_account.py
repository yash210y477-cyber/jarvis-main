"""JARVIS's own Telegram account answers texts, not just calls."""

import asyncio
from types import SimpleNamespace

from remote.telegram_calls import TelegramCallBridge


class FakeBrain:

    def chat(self, text):

        return {"response": f"heard: {text}"}


class FakeEvent:

    def __init__(self, text, user_id, outgoing=False, private=True):

        self.raw_text = text
        self._user_id = user_id
        self.out = outgoing
        self.is_private = private
        self.replies = []

    async def get_sender(self):

        return SimpleNamespace(id=self._user_id)

    async def reply(self, text):

        self.replies.append(text)


def make_bridge(monkeypatch, allowed=("9026811697",)):

    from config.settings import settings

    monkeypatch.setattr(settings, "TELEGRAM_CALL_ALLOWED", list(allowed))

    bridge = TelegramCallBridge()

    bridge.brain = FakeBrain()

    return bridge


def test_account_replies_to_allowed_number(monkeypatch):

    bridge = make_bridge(monkeypatch)

    event = FakeEvent("hey jarvis", 9026811697)

    asyncio.run(bridge._on_message(event))

    assert event.replies == ["heard: hey jarvis"]

    assert bridge.messages == 1


def test_account_ignores_unlisted_and_outgoing(monkeypatch):

    bridge = make_bridge(monkeypatch)

    stranger = FakeEvent("hey", 111222333)

    asyncio.run(bridge._on_message(stranger))

    assert stranger.replies == []

    own = FakeEvent("my own text", 9026811697, outgoing=True)

    asyncio.run(bridge._on_message(own))

    assert own.replies == []

    group = FakeEvent("group text", 9026811697, private=False)

    asyncio.run(bridge._on_message(group))

    assert group.replies == []


def test_status_counts_updates(monkeypatch):

    bridge = make_bridge(monkeypatch)

    asyncio.run(bridge._on_any(None, "dummy-update"))

    status = bridge.status()

    assert status["updates_seen"] == 1

    assert "dummy-update" in status["last_update"]

    assert status["messages"] == 0
