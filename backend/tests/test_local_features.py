import datetime
import time
from pathlib import Path

from brain import local_clock
from config.security import check_request
from config.settings import settings
from reminders.scheduler import ReminderScheduler, parse_when
from remote.telegram import TelegramBridge
from tools import clock, desktop


def test_clock_answers_without_any_provider(monkeypatch, tmp_path):

    from brain import language

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))

    language.set_language("english")

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

    # English is chosen, so even a Hinglish question is answered in English.

    assert local_clock.reply("date kya hai").startswith("Today is")

    # Auto follows the user's own message instead.

    language.set_language("auto")

    assert local_clock.reply("what is the date").startswith("Today is")

    assert local_clock.reply("date kya hai").startswith("Aaj")

    assert local_clock.reply("time kya hai").startswith("Abhi")


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


def test_a_reminder_with_no_delay_still_fires(tmp_path):
    """seconds=0 is a real delay; it used to be read as "no time given"."""

    scheduler = ReminderScheduler(tmp_path / "reminders.json")

    added = scheduler.add("stretch now", seconds=0)

    assert added["success"] is True
    assert added["in_seconds"] == 0


def test_missed_reminders_older_than_the_grace_window_are_dropped(tmp_path):
    """APScheduler can no longer fire them, so they must not stay listed."""

    import json

    path = tmp_path / "reminders.json"

    old = (datetime.datetime.now() - datetime.timedelta(days=2)).isoformat(timespec="seconds")
    fresh = (datetime.datetime.now() + datetime.timedelta(minutes=5)).isoformat(timespec="seconds")

    path.write_text(
        json.dumps({"reminders": [
            {"id": "old1", "text": "two days ago", "due": old, "created": old},
            {"id": "new1", "text": "in five minutes", "due": fresh, "created": fresh},
        ]}),
        encoding="utf-8",
    )

    scheduler = ReminderScheduler(path)

    assert [item["id"] for item in scheduler.list()] == ["new1"]


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


def test_local_token_is_required_for_changes(monkeypatch):

    monkeypatch.setattr(settings, "LOCAL_TOKEN", "secret")

    # A valid token works even from a foreign origin.
    assert check_request(
        "POST",
        {"origin": "http://evil.example", "x-jarvis-token": "secret"},
    ) is None

    # Without it nothing state-changing gets through, local UI included.
    assert check_request(
        "POST",
        {"origin": "http://localhost:5173"},
    ) is not None

    assert check_request("POST", {}) is not None

    # Reads stay open.
    assert check_request("GET", {}) is None


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


def test_set_a_reminder_and_volume_changes_are_understood():
    """"set a reminder…" used to become a timer, and "volume up 10" became 10%."""

    from tools import local_intents as li

    reminder = li.detect("set a reminder to call mom in 15 minutes")

    assert reminder["tool"] == "set_reminder"
    assert reminder["arguments"]["text"] == "call mom"
    assert reminder["arguments"]["when"] == "in 15 minutes"

    at_time = li.detect("set a reminder at 7:30 pm")

    assert at_time["tool"] == "set_reminder"
    assert at_time["arguments"]["when"] == "7:30 pm"

    louder = li.detect("volume up 10")

    assert louder["tool"] == "media_control"
    assert louder["arguments"]["action"] == "volume_up"
    assert louder["arguments"]["steps"] == 10

    assert li.detect("set volume to 40") == {
        "tool": "set_volume", "arguments": {"percent": 40}
    }

    assert li.detect("what's the volume")["tool"] == "get_volume"

    # The calendar tools work without a provider too, at least for reading.
    assert li.detect("what's on my calendar")["tool"] == "list_events"
    assert li.detect("calendar dikhao")["tool"] == "list_events"


def test_brain_answers_instantly_without_providers(monkeypatch):
    from brain.brain import FALLBACK_REPLY, Brain

    brain = Brain()

    monkeypatch.setattr(brain.ai, "providers", [])

    started = time.time()

    result = brain.chat("something completely unknown to jarvis")

    elapsed = time.time() - started

    assert result["action"] == "fallback"
    assert elapsed < 5

    # A plain sentence that says what to do, not a status code.
    assert result["response"] == FALLBACK_REPLY
    assert "No AI provider" in result["response"]
    assert "Settings" in result["response"]



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



def test_telegram_call_bridge_needs_setup(monkeypatch):

    from config.settings import settings
    from remote.telegram_calls import TelegramCallBridge
    from remote.telegram_user import TelegramUserSession

    monkeypatch.setattr(settings, "TELEGRAM_API_ID", 0)
    monkeypatch.setattr(settings, "TELEGRAM_API_HASH", "")

    bridge = TelegramCallBridge(TelegramUserSession(api_id=0, api_hash=""))

    status = bridge.status()

    assert status["enabled"] is False
    assert status["running"] is False

    started = bridge.start()

    assert started["running"] is False
    assert started["last_error"]

    assert bridge.answer(123)["success"] is False


def test_telegram_greeting_audio_is_written(tmp_path, monkeypatch):

    from remote import telegram_calls as calls

    monkeypatch.setattr(calls, "DATA_DIR", tmp_path)
    monkeypatch.setattr(calls, "GREETING_PATH", tmp_path / "greeting.wav")

    path = calls.greeting_file()

    assert path.exists()
    assert path.stat().st_size > 44



def test_multiple_commands_in_one_line_split():
    from brain.multi import split_commands

    parts = split_commands("close terminal and open calculator")

    assert parts == ["close terminal", "open calculator"]

    assert split_commands("visit youtube and search free fire in youtube") == [
        "visit youtube",
        "search free fire in youtube",
    ]

    # A single reminder sentence must stay together.
    assert split_commands("remind me to drink water and stretch in 10 minutes") == [
        "remind me to drink water and stretch in 10 minutes"
    ]


def test_visit_and_search_site_intents():
    from tools import browser, local_intents as li

    assert browser.site_url("youtube") == "https://www.youtube.com"
    assert browser.site_url("browser-tab-name") is None

    assert li.detect("visit youtube")["tool"] == "open_site"
    assert li.detect("visit youtube")["arguments"]["name"] == "youtube"

    search = li.detect("search free fire in youtube")

    assert search["tool"] == "search_site"
    assert search["arguments"] == {"query": "free fire", "site": "youtube"}

    plain = li.detect("search bahubali")

    assert plain["tool"] == "search_site"
    assert plain["arguments"]["site"] == "google"


def test_tab_jump_intent():
    from tools import local_intents as li

    intent = li.detect("open 1st tab")

    assert intent["tool"] == "browser_control"
    assert intent["arguments"] == {"action": "switch_tab", "index": 1}

    assert li.detect("switch to 3rd tab")["arguments"]["index"] == 3


def test_reminder_speaks_the_subject(tmp_path, monkeypatch):
    from reminders import scheduler as sched

    spoken = []

    monkeypatch.setattr(sched, "speak_async", lambda text: spoken.append(text))
    monkeypatch.setattr(sched, "notify", lambda *args, **kwargs: {"success": True})

    scheduler = sched.ReminderScheduler(tmp_path / "r.json")

    added = scheduler.add("drink water", "in 5 minutes")

    scheduler._fire(added["reminder"]["id"])

    assert spoken
    assert "drink water" in spoken[0]

def test_app_commands_work_in_any_word_order():

    # "spotify open" said aloud did nothing because the verb came last.
    from tools import local_intents as li

    for phrase in ("spotify open", "open spotify", "spotify kholo",
                   "kholo spotify", "chrome open karo"):

        intent = li.detect(phrase)

        assert intent["tool"] == "open_app", phrase
        assert intent["arguments"]["app_name"] in ("spotify", "chrome")

    # A misspelt app still lands on the real name.
    assert li.detect("spoitfy open")["arguments"]["app_name"] == "spotify"

    assert li.detect("close spotify")["tool"] == "close_app"
    assert li.detect("spotify band karo")["tool"] == "close_app"

    assert li.detect("terminal kholo")["arguments"]["app_name"] == "cmd"
    assert li.detect("vs code open")["arguments"]["app_name"] == "code"

    # A folder still goes to open_path, not open_app.
    assert li.detect("downloads folder kholo")["tool"] == "open_path"

def test_loose_sentences_reach_the_right_tool():

    # ChatGPT-like reading: the action words can sit anywhere.
    from tools import nlu

    assert nlu.interpret("search song on spotify") == {
        "tool": "search_site",
        "arguments": {"query": "song", "site": "spotify"},
    }

    assert nlu.interpret("spotify pe song search karo")["arguments"]["site"] == "spotify"
    assert nlu.interpret("mujhe gaana bajao youtube pe")["arguments"]["site"] == "youtube"

    assert nlu.interpret("app open spotify")["tool"] == "open_app"
    assert nlu.interpret("spotify chala do")["tool"] == "open_app"
    assert nlu.interpret("youtube kholo")["tool"] == "open_site"

    assert nlu.interpret("volume kam karo")["arguments"]["action"] == "volume_down"
    assert nlu.interpret("pause music")["arguments"]["action"] == "play_pause"
    assert nlu.interpret("next song")["arguments"]["action"] == "next"

    assert nlu.interpret("what is the weather") is None

def test_site_search_prefers_the_installed_app_only_for_apps():

    # Spotify is a desktop app, so its search belongs there; a Google or
    # YouTube search must stay on the web.
    from tools import browser

    assert browser._search_in_app("google", "song") is None
    assert browser._search_in_app("youtube", "song") is None
    assert browser._search_in_app("stackoverflow", "dict") is None


def test_call_words_are_repaired_from_the_users_own_chat(tmp_path, monkeypatch):

    from brain import vocabulary

    monkeypatch.setattr(vocabulary, "STORE", tmp_path / "vocabulary.json")

    monkeypatch.setattr(vocabulary, "_loaded", False)

    monkeypatch.setattr(vocabulary, "_words", {})

    vocabulary.learn("open postman", force_save=True)

    assert "postman" in vocabulary._words

    assert vocabulary.repair("open post man") == "open postman"

    assert vocabulary.repair("open postmain") == "open postman"

    # Ordinary sentences and already-correct words must never be rewritten.
    assert vocabulary.repair("what is the time") == "what is the time"

    assert vocabulary.repair("volume up please") == "volume up please"

    assert vocabulary.repair("open postman") == "open postman"

    assert vocabulary.repair("") == ""


def test_a_failed_tool_shows_its_own_message_not_unknown_error():
    """close_app reports a message, and that message used to be dropped."""

    from tools import local_intents

    text = local_intents.render(
        "close_app",
        {"success": False, "message": "chrome is not running."},
    )

    assert "chrome is not running" in text
    assert "unknown error" not in text


def test_close_app_says_when_windows_refused_the_kill(monkeypatch):
    """Access denied is not the same as \"not running\"."""

    from tools import launcher

    class Refused:
        returncode = 128
        stdout = ""
        stderr = "ERROR: The process could not be terminated. Reason: Access is denied."

    monkeypatch.setattr(launcher.subprocess, "run", lambda *a, **k: Refused())

    closed, message = launcher.WindowsLauncher().close("chrome")

    assert closed is False
    assert "access denied" in message.lower()
    assert "not running" not in message.lower()


def test_close_app_reports_a_missing_app_as_not_running(monkeypatch):
    from tools import launcher

    class Missing:
        returncode = 128
        stdout = ""
        stderr = "ERROR: The process \"chrome.exe\" not found."

    monkeypatch.setattr(launcher.subprocess, "run", lambda *a, **k: Missing())

    closed, message = launcher.WindowsLauncher().close("chrome")

    assert closed is False
    assert "not running" in message.lower()
