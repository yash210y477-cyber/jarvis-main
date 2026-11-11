import datetime
from pathlib import Path

from brain import local_clock
from config.security import check_request
from config.settings import settings
from reminders.scheduler import ReminderScheduler, parse_when
from remote.telegram import TelegramBridge
from tools import clock, desktop


def test_clock_answers_without_any_provider():

    now = datetime.datetime.now()

    month = local_clock.reply("what is the current month")

    assert now.strftime("%B") in month

    year = local_clock.reply("which year is it")

    assert str(now.year) in year

    date = local_clock.reply("what is the date")

    assert date.startswith("Today is")

    assert now.strftime("%A") in date

    assert now.strftime("%A") in local_clock.reply("what day is it")

    assert local_clock.reply("what time is it").startswith("It's")

    assert local_clock.reply("tell me a joke") is None


def test_clock_tool_exposes_fields():

    now = datetime.datetime.now()

    data = clock.get_datetime("month")

    assert data["success"] is True
    assert data["month"] == now.strftime("%B")
    assert data["year"] == now.year
    assert isinstance(data["month_number"], int)

    iso = clock.get_datetime("iso")

    assert iso["iso"].startswith(str(now.year))


def test_desktop_resolves_folders_and_rejects_missing():

    assert desktop.resolve("downloads folder") == Path.home() / "Downloads"
    assert desktop.resolve("Desktop") == Path.home() / "Desktop"
    assert desktop.resolve("workspace") is not None
    assert desktop.resolve("nope-not-here-xyz") is None

    assert desktop.open_path("nope-not-here-xyz")["success"] is False
    assert desktop.open_special("nope")["success"] is False


def test_parse_when_relative_and_absolute():

    now = datetime.datetime(2026, 11, 11, 9, 0)

    assert parse_when("in 10 minutes", now) == now + datetime.timedelta(minutes=10)
    assert parse_when("after 2 hours", now) == now + datetime.timedelta(hours=2)
    assert parse_when("120", now) == now + datetime.timedelta(minutes=120)

    evening = parse_when("at 7:30 pm", now)

    assert evening.hour == 19 and evening.minute == 30

    assert parse_when("at 7:30", now).hour == 19

    tomorrow = parse_when("tomorrow at 9:00 am", now)

    assert tomorrow.date() == now.date() + datetime.timedelta(days=1)

    assert parse_when("whenever", now) is None


def test_reminder_lifecycle(tmp_path):

    scheduler = ReminderScheduler(tmp_path / "reminders.json")

    added = scheduler.add("drink water", "in 5 minutes")

    assert added["success"] is True
    assert len(scheduler.list()) == 1
    assert scheduler.list()[0]["text"] == "drink water"

    assert scheduler.cancel()["success"] is True
    assert scheduler.list() == []

    assert scheduler.add("nothing", "someday")["success"] is False


def test_reminders_survive_a_restart(tmp_path):

    path = tmp_path / "reminders.json"

    first = ReminderScheduler(path)
    first.add("stretch", "in 30 minutes")

    again = ReminderScheduler(path)

    assert [item["text"] for item in again.list()] == ["stretch"]


def test_telegram_bridge_requires_token_and_filters_chats():

    bridge = TelegramBridge(token="")

    assert bridge.enabled() is False
    assert bridge.start()["running"] is False

    allowed = TelegramBridge(token="x", chat_ids=["123"])

    assert allowed.is_allowed("123") is True
    assert allowed.is_allowed("999") is False

    open_bridge = TelegramBridge(token="x", chat_ids=[])

    assert open_bridge.is_allowed("999") is True


def test_local_token_bypasses_foreign_origin(monkeypatch):

    monkeypatch.setattr(settings, "LOCAL_TOKEN", "secret")

    assert check_request(
        "POST",
        {"origin": "http://evil.example", "x-jarvis-token": "secret"},
    ) is None

    assert check_request(
        "POST",
        {"origin": "http://evil.example"},
    ) is not None

    assert check_request(
        "POST",
        {"origin": "http://localhost:5173"},
    ) is None


def test_briefing_mentions_the_day_and_stats(tmp_path):

    from reminders.briefing import build_briefing

    scheduler = ReminderScheduler(tmp_path / "r.json")

    text = build_briefing(None, scheduler.list())

    assert datetime.datetime.now().strftime("%A") in text
    assert "CPU" in text
