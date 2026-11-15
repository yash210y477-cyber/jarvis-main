"""Dated chat history: every conversation gets a chat with a date."""

import time

from memory.storage import Storage


def make(tmp_path):
    return Storage(tmp_path / "jarvis.db")


def test_every_message_lands_in_a_dated_chat(tmp_path):
    storage = make(tmp_path)

    storage.add_message("user", "open spotify")
    storage.add_message("assistant", "Spotify khul gaya.")

    chats = storage.chats()

    assert len(chats) == 1
    assert chats[0]["title"] == "open spotify"
    assert chats[0]["messages"] == 2
    assert chats[0]["started_at"] > 0


def test_a_long_pause_starts_a_new_chat(tmp_path):
    storage = make(tmp_path)

    storage.add_message("user", "first chat")
    storage.add_message("assistant", "ok")

    # Pretend the last chat was a day ago.
    storage.conn.execute(
        "UPDATE chats SET updated_at = ?", (time.time() - 24 * 3600,)
    )
    storage.conn.commit()

    storage.add_message("user", "second chat")

    chats = storage.chats()

    assert len(chats) == 2
    assert chats[0]["title"] == "second chat"


def test_a_short_pause_keeps_the_same_chat(tmp_path):
    storage = make(tmp_path)

    storage.add_message("user", "hello")
    storage.add_message("user", "again")

    assert len(storage.chats()) == 1


def test_reading_one_chat_back(tmp_path):
    storage = make(tmp_path)

    first = storage.current_chat()
    storage.add_message("user", "pehli baat", chat_id=first)

    second = storage.start_chat("alag chat")
    storage.add_message("user", "doosri baat", chat_id=second)

    messages = storage.chat_messages(first)

    assert [m["text"] for m in messages] == ["pehli baat"]
    assert messages[0]["at"] > 0


def test_deleting_a_chat_removes_its_messages(tmp_path):
    storage = make(tmp_path)

    storage.add_message("user", "delete me")
    chat_id = storage.chats()[0]["id"]

    assert storage.delete_chat(chat_id) is True
    assert storage.chats() == []
    assert storage.chat_messages(chat_id) == []


def test_old_messages_without_a_chat_get_one(tmp_path):
    path = tmp_path / "jarvis.db"

    storage = Storage(path)

    # A database from before chats existed.
    storage.conn.execute("INSERT INTO messages (role, text) VALUES ('user', 'purani baat')")
    storage.conn.commit()
    storage.conn.execute("UPDATE messages SET chat_id = NULL")
    storage.conn.commit()
    storage.close()

    reopened = Storage(path)
    chats = reopened.chats()

    assert len(chats) == 1
    assert chats[0]["title"] == "purani baat"


def test_clearing_the_conversation_clears_chats_too(tmp_path):
    storage = make(tmp_path)

    storage.add_message("user", "bye")

    storage.clear_messages()

    assert storage.chats() == []
    assert storage.message_count() == 0
