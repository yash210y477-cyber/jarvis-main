import json

from memory.storage import Storage


def make_storage(tmp_path, name="test.db"):

    return Storage(str(tmp_path / name))


def test_profile_roundtrip(tmp_path):

    storage = make_storage(tmp_path)

    storage.set_profile("name", "Yash")

    assert storage.get_profile()["name"] == "Yash"

    # Unset profile fields still exist so callers never need .get().
    assert storage.get_profile()["city"] == ""

    storage.clear_profile()

    assert storage.get_profile()["name"] == ""


def test_facts_upsert(tmp_path):

    storage = make_storage(tmp_path)

    storage.set_fact("editor", "VS Code")

    storage.set_fact("editor", "Neovim")

    assert storage.get_fact("editor") == "Neovim"

    assert storage.facts() == {"editor": "Neovim"}


def test_messages_and_trim(tmp_path):

    storage = make_storage(tmp_path)

    for index in range(5):

        storage.add_message("user", f"message {index}")

    assert storage.message_count() == 5

    assert [item["text"] for item in storage.messages(limit=2)] == [
        "message 3",
        "message 4",
    ]

    removed = storage.trim_messages(2)

    assert removed >= 3

    remaining = storage.messages()

    assert len(remaining) == 2

    assert remaining[-1]["text"] == "message 4"


def test_messages_after_keeps_ids_monotonic(tmp_path):

    storage = make_storage(tmp_path)

    first = storage.add_message("user", "hello")

    storage.add_message("assistant", "hi")

    pending = storage.messages_after(first - 1)

    assert [item["text"] for item in pending] == ["hello", "hi"]


def test_summaries(tmp_path):

    storage = make_storage(tmp_path)

    assert storage.latest_summary() is None

    storage.save_summary("first summary", message_count=10)

    storage.save_summary("second summary", message_count=20)

    latest = storage.latest_summary()

    assert latest["summary"] == "second summary"

    assert latest["message_count"] == 20

    storage.clear_summaries()

    assert storage.latest_summary() is None


def test_reset_clears_data(tmp_path):

    storage = make_storage(tmp_path)

    storage.set_profile("name", "Yash")

    storage.set_fact("bike", "RE")

    storage.add_message("user", "hello")

    storage.save_summary("summary")

    storage.reset()

    assert storage.get_profile()["name"] == ""

    assert storage.facts() == {}

    assert storage.message_count() == 0

    assert storage.latest_summary() is None


def test_legacy_json_migration(tmp_path):

    legacy = {
        "profile": {"name": "Legacy", "email": "legacy@example.com"},
        "preferences": {"theme": "dark"},
        "facts": [{"key": "bike", "value": "Classic 350"}],
        "conversation": [
            {"role": "user", "text": "hello"},
            {"role": "assistant", "text": "hi"},
        ],
    }

    (tmp_path / "memory.json").write_text(
        json.dumps(legacy),
        encoding="utf-8",
    )

    storage = Storage(str(tmp_path / "migrated.db"))

    assert storage.get_profile()["name"] == "Legacy"

    assert storage.get_fact("bike") == "Classic 350"

    assert storage.get_fact("theme") == "dark"

    assert storage.message_count() == 2

    # Re-opening must not import twice.
    storage.close()

    again = Storage(str(tmp_path / "migrated.db"))

    assert again.message_count() == 2
