import json
import os
import sqlite3
import time
from pathlib import Path


PROFILE_FIELDS = ("name", "email", "city", "occupation")


def data_dir() -> Path:
    """Folder for everything JARVIS remembers (tests override it via env)."""

    override = os.getenv("JARVIS_DATA_DIR")

    if override:

        return Path(override)

    return Path(__file__).resolve().parent.parent / "data"


class Storage:
    """SQLite storage for profile, facts, conversation, notes and summaries.

    Older databases added NOT NULL `created_at` / `updated_at` columns, so
    inserts check the real table shape instead of assuming one schema.

    NOTE:
    No other module should talk to the database file directly.
    """

    SCHEMA = (
        "CREATE TABLE IF NOT EXISTS profile ("
        "key TEXT PRIMARY KEY, value TEXT NOT NULL DEFAULT '')",
        "CREATE TABLE IF NOT EXISTS facts ("
        "key TEXT PRIMARY KEY, value TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS messages ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL, "
        "text TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS notes ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS summaries ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, summary TEXT NOT NULL, "
        "message_count INTEGER NOT NULL DEFAULT 0)",
        "CREATE TABLE IF NOT EXISTS meta ("
        "key TEXT PRIMARY KEY, value TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS chats ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL DEFAULT '', "
        "created_at REAL NOT NULL DEFAULT 0, updated_at REAL NOT NULL DEFAULT 0)",
    )

    # A long pause starts a new chat, the way a chat app does.
    CHAT_GAP = 6 * 3600

    def __init__(self, path=None):

        if path:

            self.path = Path(path)

        else:

            self.path = data_dir() / "jarvis.db"

        if str(self.path.parent) not in ("", "."):

            self.path.parent.mkdir(parents=True, exist_ok=True)

        # uvicorn/TestClient run endpoints in worker threads.
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)

        self.conn.row_factory = sqlite3.Row

        self.initialize()

        self.migrate_legacy()

    # -----------------------------
    # SCHEMA
    # -----------------------------

    def initialize(self):

        for statement in self.SCHEMA:

            self.conn.execute(statement)

        self._ensure_message_columns()

        for field in PROFILE_FIELDS:

            self.conn.execute(
                "INSERT OR IGNORE INTO profile (key, value) VALUES (?, '')",
                (field,),
            )

        self.conn.commit()

    def columns(self, table: str) -> dict:

        rows = self.conn.execute(f"PRAGMA table_info({table})").fetchall()

        return {row["name"]: dict(row) for row in rows}

    def migrate_legacy(self):

        """Import the old data/memory.json once, next to this database."""

        if self.get_meta("legacy_imported"):

            return

        # A populated database always wins over the old JSON file.
        if self.message_count() or self.facts():

            self.set_meta("legacy_imported", "1")

            return

        legacy = self.path.parent / "memory.json"

        if legacy.exists():

            try:

                data = json.loads(legacy.read_text(encoding="utf-8"))

            except Exception:

                data = {}

            if isinstance(data, dict):

                self._import_legacy(data)

        self.set_meta("legacy_imported", "1")

    def _import_legacy(self, data: dict):

        for key, value in (data.get("profile") or {}).items():

            if value:

                self.set_profile(key, value)

        preferences = data.get("preferences") or {}

        for key, value in preferences.items():

            if value:

                self.set_fact(key, str(value))

        for item in data.get("facts") or []:

            if isinstance(item, dict) and item.get("key"):

                self.set_fact(item["key"], str(item.get("value", "")))

        for item in data.get("notes") or []:

            if item:

                self.add_note(str(item))

        for message in data.get("conversation") or []:

            if isinstance(message, dict) and message.get("role"):

                self.add_message(
                    message["role"],
                    str(message.get("text", "")),
                )

    # -----------------------------
    # META
    # -----------------------------

    def get_meta(self, key: str):

        row = self.conn.execute(
            "SELECT value FROM meta WHERE key = ?",
            (key,),
        ).fetchone()

        return row["value"] if row else None

    def set_meta(self, key: str, value: str):

        self.conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

        self.conn.commit()

    # -----------------------------
    # PROFILE
    # -----------------------------

    def set_profile(self, key: str, value: str):

        self.conn.execute(
            "INSERT INTO profile (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, (value or "").strip()),
        )

        self.conn.commit()

    def get_profile(self) -> dict:

        rows = self.conn.execute("SELECT key, value FROM profile").fetchall()

        profile = {field: "" for field in PROFILE_FIELDS}

        for row in rows:

            profile[row["key"]] = row["value"]

        return profile

    def clear_profile(self):

        for field in PROFILE_FIELDS:

            self.set_profile(field, "")

        self.conn.execute(
            "DELETE FROM profile WHERE key NOT IN (?, ?, ?, ?)",
            PROFILE_FIELDS,
        )

        self.conn.commit()

    # -----------------------------
    # FACTS
    # -----------------------------

    def set_fact(self, key: str, value: str):

        columns = self.columns("facts")

        if "updated_at" in columns:

            self.conn.execute(
                "INSERT INTO facts (key, value, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                "updated_at = excluded.updated_at",
                (key, value, time.time()),
            )

        else:

            self.conn.execute(
                "INSERT INTO facts (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

        self.conn.commit()

    def get_fact(self, key: str):

        row = self.conn.execute(
            "SELECT value FROM facts WHERE key = ?",
            (key,),
        ).fetchone()

        return row["value"] if row else None

    def facts(self) -> dict:

        rows = self.conn.execute("SELECT key, value FROM facts ORDER BY key").fetchall()

        return {row["key"]: row["value"] for row in rows}

    def delete_fact(self, key: str) -> bool:

        cursor = self.conn.execute("DELETE FROM facts WHERE key = ?", (key,))

        self.conn.commit()

        return cursor.rowcount > 0

    def clear_facts(self):

        self.conn.execute("DELETE FROM facts")

        self.conn.commit()

    # -----------------------------
    # NOTES
    # -----------------------------

    def add_note(self, text: str):

        self.conn.execute("INSERT INTO notes (text) VALUES (?)", (text,))

        self.conn.commit()

        return self.notes()

    def notes(self) -> list:

        rows = self.conn.execute("SELECT text FROM notes ORDER BY id").fetchall()

        return [row["text"] for row in rows]

    def delete_note(self, index: int) -> bool:

        rows = self.conn.execute("SELECT id FROM notes ORDER BY id").fetchall()

        if not 0 <= index < len(rows):

            return False

        self.conn.execute("DELETE FROM notes WHERE id = ?", (rows[index]["id"],))

        self.conn.commit()

        return True

    # -----------------------------
    # CHATS (dated history)
    # -----------------------------

    def _ensure_message_columns(self):

        columns = self.columns("messages")

        if "created_at" not in columns:

            self.conn.execute(
                "ALTER TABLE messages ADD COLUMN created_at REAL NOT NULL DEFAULT 0"
            )

        if "chat_id" not in columns:

            self.conn.execute("ALTER TABLE messages ADD COLUMN chat_id INTEGER")

        self.conn.commit()

        self._adopt_orphan_messages()

    def _adopt_orphan_messages(self):
        """Older messages have no chat; put them in one dated chat."""

        row = self.conn.execute(
            "SELECT COUNT(*) AS total FROM messages WHERE chat_id IS NULL"
        ).fetchone()

        if not row or not int(row["total"] or 0):

            return

        try:

            started = Path(self.path).stat().st_mtime

        except OSError:

            started = time.time()

        cursor = self.conn.execute(
            "INSERT INTO chats (title, created_at, updated_at) VALUES ('', ?, ?)",
            (started, started),
        )

        self.conn.execute(
            "UPDATE messages SET chat_id = ? WHERE chat_id IS NULL", (cursor.lastrowid,)
        )

        self._touch_chat(cursor.lastrowid, self._first_user_text(cursor.lastrowid))

        self.conn.commit()

    def _first_user_text(self, chat_id) -> str:

        row = self.conn.execute(
            "SELECT text FROM messages WHERE chat_id = ? AND role = 'user' "
            "ORDER BY id LIMIT 1",
            (chat_id,),
        ).fetchone()

        return (row["text"] if row else "") or ""

    def _touch_chat(self, chat_id, title: str = ""):

        now = time.time()

        if title:

            self.conn.execute(
                "UPDATE chats SET updated_at = ?, "
                "title = CASE WHEN title = '' THEN ? ELSE title END WHERE id = ?",
                (now, title.strip()[:80], chat_id),
            )

        else:

            self.conn.execute(
                "UPDATE chats SET updated_at = ? WHERE id = ?", (now, chat_id)
            )

    def start_chat(self, title: str = "") -> int:

        now = time.time()

        cursor = self.conn.execute(
            "INSERT INTO chats (title, created_at, updated_at) VALUES (?, ?, ?)",
            ((title or "").strip()[:80], now, now),
        )

        self.conn.commit()

        return int(cursor.lastrowid)

    def current_chat(self, gap=None) -> int:
        """The chat this message belongs to; a long pause starts a new one."""

        gap = self.CHAT_GAP if gap is None else gap

        row = self.conn.execute(
            "SELECT id, updated_at FROM chats ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if row and (time.time() - float(row["updated_at"] or 0)) < gap:

            return int(row["id"])

        return self.start_chat()

    def chats(self, limit: int = 60) -> list:
        """Every chat, newest first, with its date and last line."""

        rows = self.conn.execute(
            "SELECT c.id, c.title, c.created_at, c.updated_at, "
            "COUNT(m.id) AS total FROM chats c "
            "LEFT JOIN messages m ON m.chat_id = c.id "
            "GROUP BY c.id ORDER BY c.updated_at DESC LIMIT ?",
            (int(limit),),
        ).fetchall()

        items = []

        for row in rows:

            last = self.conn.execute(
                "SELECT text FROM messages WHERE chat_id = ? ORDER BY id DESC LIMIT 1",
                (row["id"],),
            ).fetchone()

            items.append(
                {
                    "id": int(row["id"]),
                    "title": (row["title"] or "").strip()
                    or (self._first_user_text(row["id"])[:60] or "New chat"),
                    "started_at": float(row["created_at"] or 0),
                    "updated_at": float(row["updated_at"] or 0),
                    "messages": int(row["total"] or 0),
                    "preview": (last["text"] if last else "")[:120],
                }
            )

        return items

    def chat_messages(self, chat_id) -> list:

        rows = self.conn.execute(
            "SELECT id, role, text, created_at FROM messages "
            "WHERE chat_id = ? ORDER BY id",
            (int(chat_id),),
        ).fetchall()

        return [
            {
                "id": row["id"],
                "role": row["role"],
                "text": row["text"],
                "at": float(row["created_at"] or 0),
            }
            for row in rows
        ]

    def delete_chat(self, chat_id) -> bool:

        self.conn.execute("DELETE FROM messages WHERE chat_id = ?", (int(chat_id),))

        cursor = self.conn.execute("DELETE FROM chats WHERE id = ?", (int(chat_id),))

        self.conn.commit()

        return cursor.rowcount > 0

    # -----------------------------
    # CONVERSATION
    # -----------------------------

    def add_message(self, role: str, text: str, chat_id=None) -> int:

        chat_id = int(chat_id or self.current_chat())

        cursor = self.conn.execute(
            "INSERT INTO messages (role, text, created_at, chat_id) VALUES (?, ?, ?, ?)",
            (role, text, time.time(), chat_id),
        )

        self._touch_chat(chat_id, text if role == "user" else "")

        self.conn.commit()

        return cursor.lastrowid

    def messages(self, limit=None) -> list:

        rows = self.conn.execute(
            "SELECT id, role, text FROM messages ORDER BY id"
        ).fetchall()

        items = [
            {"id": row["id"], "role": row["role"], "text": row["text"]}
            for row in rows
        ]

        if limit:

            return items[-limit:]

        return items

    def messages_after(self, message_id: int) -> list:

        rows = self.conn.execute(
            "SELECT id, role, text FROM messages WHERE id > ? ORDER BY id",
            (message_id,),
        ).fetchall()

        return [
            {"id": row["id"], "role": row["role"], "text": row["text"]}
            for row in rows
        ]

    def message_count(self) -> int:

        row = self.conn.execute("SELECT COUNT(*) AS total FROM messages").fetchone()

        return int(row["total"])

    def trim_messages(self, keep: int) -> int:

        total = self.message_count()

        if keep < 0:

            keep = 0

        if total <= keep:

            return 0

        rows = self.conn.execute(
            "SELECT id FROM messages ORDER BY id DESC LIMIT ?",
            (keep,),
        ).fetchall()

        if rows:

            lowest = min(row["id"] for row in rows)

            self.conn.execute("DELETE FROM messages WHERE id < ?", (lowest,))

        else:

            self.conn.execute("DELETE FROM messages")

        self.conn.commit()

        return total - keep

    def clear_messages(self):

        self.conn.execute("DELETE FROM messages")

        self.conn.execute("DELETE FROM chats")

        self.conn.commit()

    # -----------------------------
    # SUMMARIES
    # -----------------------------

    def save_summary(self, summary: str, message_count: int = 0):

        if "created_at" in self.columns("summaries"):

            self.conn.execute(
                "INSERT INTO summaries (summary, message_count, created_at) "
                "VALUES (?, ?, ?)",
                (summary, int(message_count or 0), time.time()),
            )

        else:

            self.conn.execute(
                "INSERT INTO summaries (summary, message_count) VALUES (?, ?)",
                (summary, int(message_count or 0)),
            )

        self.conn.commit()

    def latest_summary(self):

        row = self.conn.execute(
            "SELECT summary, message_count FROM summaries ORDER BY id DESC LIMIT 1"
        ).fetchone()

        if not row:

            return None

        return {
            "summary": row["summary"],
            "message_count": row["message_count"],
        }

    def clear_summaries(self):

        self.conn.execute("DELETE FROM summaries")

        self.conn.commit()

    # -----------------------------
    # RESET / CLOSE
    # -----------------------------

    def reset(self):

        for table in ("messages", "notes", "summaries", "facts", "chats"):

            self.conn.execute(f"DELETE FROM {table}")

        self.conn.commit()

        self.clear_profile()

        self.set_meta("legacy_imported", "1")

    def close(self):

        try:

            self.conn.close()

        except Exception:

            pass
