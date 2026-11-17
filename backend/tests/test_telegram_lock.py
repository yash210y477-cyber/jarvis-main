"""One bot, one poller: the lock file must not block the bot forever.

Telegram answers a second getUpdates with "Conflict", so only one JARVIS may
read the bot. The lock used to hold a bare pid; Windows reuses pids, so a lock
left behind by a dead run could point at an unrelated process and keep the bot
offline until the file was deleted by hand.
"""

import json
import os

import psutil

from remote import telegram


def bridge_with(monkeypatch, tmp_path):
    lock = tmp_path / "telegram_bot.lock"
    monkeypatch.setattr(telegram, "LOCK_PATH", lock)
    return telegram.TelegramBridge(brain=None, token="test-token", chat_ids=[]), lock


def test_a_lock_left_by_a_reused_pid_is_taken_over(monkeypatch, tmp_path):
    bridge, lock = bridge_with(monkeypatch, tmp_path)
    # Our own pid, but the start time of some older process: not a real owner.
    lock.write_text(json.dumps({"pid": os.getpid(), "started": 1.0}), encoding="utf-8")

    assert bridge._acquire_lock() is True

    written = json.loads(lock.read_text(encoding="utf-8"))
    assert written["pid"] == os.getpid()
    assert written["started"] > 1


def test_a_live_other_instance_keeps_the_bot(monkeypatch, tmp_path):
    bridge, lock = bridge_with(monkeypatch, tmp_path)
    other = psutil.Process(os.getppid())
    lock.write_text(
        json.dumps({"pid": other.pid, "started": other.create_time()}), encoding="utf-8"
    )

    assert bridge._acquire_lock() is False
    assert str(other.pid) in (bridge.last_error or "")


def test_an_unreadable_lock_is_taken_over(monkeypatch, tmp_path):
    bridge, lock = bridge_with(monkeypatch, tmp_path)
    lock.write_text("not-a-pid", encoding="utf-8")

    assert bridge._acquire_lock() is True


def test_an_old_plain_pid_lock_is_still_respected(monkeypatch, tmp_path):
    bridge, lock = bridge_with(monkeypatch, tmp_path)
    lock.write_text(str(os.getppid()), encoding="utf-8")

    assert bridge._acquire_lock() is False


def test_releasing_removes_the_lock(monkeypatch, tmp_path):
    bridge, lock = bridge_with(monkeypatch, tmp_path)
    assert bridge._acquire_lock() is True
    assert lock.exists()

    bridge._release_lock()

    assert not lock.exists()
