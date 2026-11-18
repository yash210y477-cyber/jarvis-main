"""Email and calendar tools: setup errors, a fake SMTP server, and real .ics."""

import datetime
import json

from config.settings import settings


def _forget(monkeypatch):
    for name in (
        "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM",
        "SMTP_SSL", "IMAP_HOST", "IMAP_PORT",
    ):
        monkeypatch.setattr(settings, name, "" if "PORT" not in name else 465, raising=False)


def test_email_needs_setup_before_sending(monkeypatch):
    from tools import mail

    _forget(monkeypatch)

    result = mail.send_email("friend@example.com", "Hello", "How are you?")

    assert result["success"] is False
    assert "SMTP" in result["error"]

    inbox = mail.read_inbox()

    assert inbox["success"] is False
    assert "IMAP" in inbox["error"]


def test_email_is_sent_through_smtp(monkeypatch):
    from tools import mail

    sent = {}

    class FakeServer:
        def __init__(self, host, port, timeout=None, context=None):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def login(self, user, password):
            sent["login"] = (user, password)

        def send_message(self, message, to_addrs=None):
            sent["to"] = to_addrs
            sent["subject"] = message["Subject"]
            sent["body"] = message.get_content().strip()

    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", FakeServer)
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com", raising=False)
    monkeypatch.setattr(settings, "SMTP_PORT", 465, raising=False)
    monkeypatch.setattr(settings, "SMTP_USER", "me@example.com", raising=False)
    monkeypatch.setattr(settings, "SMTP_PASSWORD", "app-password", raising=False)
    monkeypatch.setattr(settings, "SMTP_FROM", "", raising=False)
    monkeypatch.setattr(settings, "SMTP_SSL", True, raising=False)

    result = mail.send_email(
        "friend@example.com", "Dinner", "See you at 8.", cc="mom@example.com"
    )

    assert result["success"] is True
    assert sent["host"] == "smtp.example.com"
    assert sent["to"] == ["friend@example.com", "mom@example.com"]
    assert sent["subject"] == "Dinner"
    assert "See you at 8." in sent["body"]


def test_a_bad_address_is_refused(monkeypatch):
    from tools import mail

    _forget(monkeypatch)

    assert mail.send_email("not-an-address", "Hi", "There")["success"] is False
    assert mail.send_email("friend@example.com", "", "")["success"] is False


def test_calendar_event_becomes_a_real_ics_file(monkeypatch, tmp_path):
    from pathlib import Path

    from tools import agenda

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))

    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)

    result = agenda.add_event(
        "Dentist", "tomorrow at 9:00 am", duration_minutes=30, location="Clinic"
    )

    assert result["success"] is True
    assert result["path"].endswith(".ics")

    text = Path(result["path"]).read_text(encoding="utf-8")

    assert "BEGIN:VEVENT" in text
    assert "SUMMARY:Dentist" in text
    assert "LOCATION:Clinic" in text
    assert text.count("DTSTART:") == 1 and text.count("DTEND:") == 1
    assert result["event"]["duration_minutes"] == 30
    assert result["event"]["start"].startswith(tomorrow.strftime("%Y-%m-%d") + "T09:00")

    listed = agenda.list_events(days=7)

    assert listed["success"] is True
    assert [item["title"] for item in listed["events"]] == ["Dentist"]

    stored = json.loads((tmp_path / "agenda.json").read_text(encoding="utf-8"))

    assert stored["events"][0]["title"] == "Dentist"


def test_calendar_refuses_an_unreadable_time(monkeypatch, tmp_path):
    from tools import agenda

    monkeypatch.setenv("JARVIS_DATA_DIR", str(tmp_path))

    result = agenda.add_event("Dentist", "whenever")

    assert result["success"] is False
    assert "when" in result["error"].lower()


def test_inbox_phrases_go_to_the_mail_tool():
    from tools import local_intents

    assert local_intents.detect("read my inbox")["tool"] == "read_inbox"
    assert local_intents.detect("any new mail?")["tool"] == "read_inbox"
    assert local_intents.detect("show my unread email")["arguments"]["unread_only"] is True

    # Reading a real file must still reach the file tool.
    assert local_intents.detect("read backend/README.md")["tool"] == "read_file"


def test_both_tools_are_registered():
    from tools import builtin

    registry = builtin.REGISTRY

    assert registry.exists("send_email")
    assert registry.exists("read_inbox")
    assert registry.exists("add_event")
    assert registry.exists("list_events")

    assert registry.get("send_email")["permission"] == "confirm"
    assert registry.get("read_inbox")["permission"] == "confirm"
    assert registry.get("add_event")["permission"] == "auto"
