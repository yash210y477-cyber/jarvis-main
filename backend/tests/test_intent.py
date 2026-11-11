import pytest

from brain.entity import EntityExtractor
from brain.intent import IntentEngine


@pytest.fixture
def engine():

    return IntentEngine()


@pytest.mark.parametrize(
    "text,intent,target",
    [
        ("open chrome", "open_app", "chrome"),
        ("launch vs code", "open_app", "vs code"),
        ("open google.com", "open_website", "google.com"),
        ("visit github.com", "open_website", "github.com"),
        ("open website example.com", "open_website", "example.com"),
        ("search for python decorators", "search_web", "python decorators"),
        ("close chrome", "close_app", "chrome"),
        ("what is my name", "recall", ""),
        ("system status", "system_status", ""),
        ("tell me a joke", "chat", ""),
    ],
)
def test_intent_detection(engine, text, intent, target):

    command = engine.detect(text)

    assert command["intent"] == intent

    if target:

        assert command["target"] == target


def test_open_website_wins_over_open_app(engine):

    command = engine.detect("open google.com")

    assert command["intent"] == "open_website"

    command = engine.detect("open chrome")

    assert command["intent"] == "open_app"


def test_remember_extracts_every_fact():

    extractor = EntityExtractor()

    entities = extractor.extract_all(
        "my name is Yash and I live in Delhi and my favourite editor is VS Code"
    )

    fields = {entity["field"]: entity["value"] for entity in entities}

    assert fields == {
        "name": "Yash",
        "city": "Delhi",
        "editor": "VS Code",
    }


def test_remember_intent_carries_entities(engine):

    command = engine.detect("my name is Yash")

    assert command["intent"] == "remember"

    assert command["entities"] == [{"field": "name", "value": "Yash"}]


def test_generic_remember_fact(engine):

    command = engine.detect("remember my wifi password is hunter2")

    assert command["intent"] == "remember"

    assert command["entities"][0]["field"] == "wifi_password"

    assert command["entities"][0]["value"] == "hunter2"


def test_bare_i_am_is_not_a_fact(engine):

    # "I am tired" used to be stored as the user's occupation.
    assert engine.detect("i am tired")["intent"] == "chat"
