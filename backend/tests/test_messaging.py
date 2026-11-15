import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import local_intents, messaging


def test_message_to_intent_names_platform():
    got = local_intents.detect("message hey to mumma on telegram")

    assert got == {
        "tool": "send_message",
        "arguments": {
            "platform": "telegram",
            "contact": "mumma",
            "text": "hey",
            "confirm": True,
        },
    }


def test_message_intent_defaults_to_whatsapp():
    got = local_intents.detect("send message to mumma saying hey")

    assert got["arguments"]["platform"] == "whatsapp"
    assert got["arguments"]["text"] == "hey"


def test_hinglish_message_intent_drops_the_preposition():
    got = local_intents.detect("mumma ko hey message bhejo whatsapp par")

    assert got["arguments"]["contact"] == "mumma"
    assert got["arguments"]["text"] == "hey"


def test_opening_an_app_is_not_a_message():
    assert local_intents.detect("open whatsapp")["tool"] == "open_app"


def test_platform_aliases():
    assert messaging._resolve("wa")[0] == "whatsapp"
    assert messaging._resolve("insta")[0] == "instagram"
    assert messaging._resolve("telegram par")[0] == "telegram"


def test_unknown_platform_uses_its_website():
    _, spec = messaging._resolve("youtube")

    assert spec["strategy"] == "web"
    assert "youtube" in spec["web"]


def test_phone_link_needs_a_number():
    spec = messaging.PLATFORMS["whatsapp"]

    assert messaging._link_shortcut({"phone": "+91 98765 43210"}, spec, "hi") == (
        "https://wa.me/919876543210?text=hi"
    )
    assert messaging._link_shortcut({}, spec, "hi") == ""
