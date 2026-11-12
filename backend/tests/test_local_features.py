import datetime
import time
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


def test_local_intents_cover_system_commands():
    from tools import local_intents as li

    assert li.detect("open settings")["tool"] == "open_special"
    assert li.detect("open youtube.com")["tool"] == "open_website"
    assert li.detect("lock the screen")["tool"] == "lock_screen"
    assert li.detect("shut down the computer")["arguments"]["action"] == "shutdown"
    assert li.detect("reboot")["arguments"]["action"] == "restart"
    assert li.detect("open chrome")["tool"] == "open_app"


def test_reminder_duration_without_in_prefix_is_relative():
    from tools import local_intents as li
    from reminders.scheduler import parse_when

    intent = li.detect("remind me to stretch in 2 minutes")

    assert intent["tool"] == "set_reminder"
    assert intent["arguments"]["when"].startswith("in ")

    due = parse_when("2 minutes")

    assert due < datetime.datetime.now() + datetime.timedelta(minutes=5)


def test_brain_answers_instantly_without_providers(monkeypatch):
    from brain.brain import Brain

    brain = Brain()

    monkeypatch.setattr(brain.ai, "providers", [])

    started = time.time()

    result = brain.chat("something completely unknown to jarvis")

    elapsed = time.time() - started

    assert result["action"] == "fallback"
    assert elapsed < 5
    assert "open chrome" in result["response"]



def test_local_intents_route_apps_and_bulk_window_commands():

    from tools import local_intents as li

    assert li.detect("open whatsapp")["tool"] == "open_app"
    assert li.detect("open telegram")["tool"] == "open_app"
    assert li.detect("close chrome")["tool"] == "close_app"
    assert li.detect("minimize all windows")["tool"] == "minimize_all"
    assert li.detect("close all apps")["tool"] == "close_all_windows"
    assert li.detect("open settings")["arguments"]["app"] == "settings"
    assert li.detect("open youtube.com")["tool"] == "open_website"


def test_clock_answers_today_day_separately():

    from brain import local_clock

    assert local_clock.detect("what is today day") == "weekday"
    assert local_clock.detect("which day is today") == "weekday"
    assert local_clock.detect("what is the current month") == "month"
    assert local_clock.detect("which year is it") == "year"



def test_local_intents_browser_tabs_and_volume_levels():

    from tools import local_intents as li

    assert li.detect("open new tab")["arguments"]["action"] == "new_tab"
    assert li.detect("open a new window")["arguments"]["action"] == "new_window"
    assert li.detect("close the 2nd tab")["arguments"] == {
        "action": "close_tab",
        "index": 2,
    }
    assert li.detect("close the last tab")["arguments"]["index"] == 9
    assert li.detect("close this tab")["arguments"]["action"] == "close_tab"
    assert li.detect("volume down to 10")["arguments"] == {"percent": 10}
    assert li.detect("volume up to 85")["arguments"] == {"percent": 85}
    assert li.detect("set volume to 40")["arguments"] == {"percent": 40}
    assert li.detect("volume up")["arguments"]["action"] == "volume_up"
