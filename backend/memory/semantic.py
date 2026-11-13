"""Semantic memory: find things by meaning instead of exact words.

Everything runs on this computer and never needs an API key. Text is turned
into embeddings by a local sentence-transformers model; if that model cannot be
loaded, a deterministic hashed n-gram embedding keeps search working offline.

Vectors live in the same SQLite database as the rest of the memory, so a search
like "mera AI desktop project" still finds "User is developing a React-based AI
assistant named JARVIS."
"""

import hashlib
import logging
import re
import sqlite3
import threading
import time

import numpy as np

from config.settings import settings
from memory.storage import Storage


log = logging.getLogger("jarvis.semantic")

HASH_DIM = 512

_WORD = re.compile(r"[a-z0-9\u0900-\u097F]+")


class HashingEmbedder:
    """Offline fallback: hashed word, character n-gram and bigram features."""

    name = "hash-ngram"
    dim = HASH_DIM

    def encode(self, texts):

        rows = [self._one(text) for text in texts]

        if not rows:

            return np.zeros((0, HASH_DIM), dtype=np.float32)

        return np.asarray(rows, dtype=np.float32)

    def _one(self, text):

        vector = np.zeros(HASH_DIM, dtype=np.float32)

        tokens = _WORD.findall((text or "").lower())

        for token in tokens:

            self._add(vector, token, 1.0)

            for size in (3, 4):

                for start in range(0, max(1, len(token) - size + 1)):

                    self._add(vector, token[start:start + size], 0.4)

        for first, second in zip(tokens, tokens[1:]):

            self._add(vector, f"{first} {second}", 0.7)

        norm = float(np.linalg.norm(vector))

        if norm > 0:

            vector /= norm

        return vector

    @staticmethod
    def _add(vector, token, weight):

        digest = hashlib.md5(token.encode("utf-8")).digest()

        index = int.from_bytes(digest[:4], "little") % HASH_DIM

        sign = 1.0 if digest[4] % 2 == 0 else -1.0

        vector[index] += sign * weight


class TransformerEmbedder:
    """Local sentence-transformers model (downloaded once, then offline)."""

    def __init__(self, model_name):

        from sentence_transformers import SentenceTransformer

        self.name = model_name
        self.model = SentenceTransformer(model_name)
        # sentence-transformers renamed this in 6.x; support both.
        size = getattr(self.model, "get_embedding_dimension", None) or (
            self.model.get_sentence_embedding_dimension
        )

        self.dim = int(size() or 384)

    def encode(self, texts):

        vectors = self.model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=32,
        )

        return np.asarray(vectors, dtype=np.float32)


_EMBEDDER = None
_EMBEDDER_LOCK = threading.Lock()


def load_embedder():
    """One embedder for the whole process; falls back when the model is absent."""

    global _EMBEDDER

    if _EMBEDDER is not None:

        return _EMBEDDER

    with _EMBEDDER_LOCK:

        if _EMBEDDER is not None:

            return _EMBEDDER

        if settings.SEMANTIC_MEMORY:

            try:

                _EMBEDDER = TransformerEmbedder(settings.SEMANTIC_MODEL)

                log.info("Semantic memory using %s", _EMBEDDER.name)

                return _EMBEDDER

            except Exception as error:

                log.warning(
                    "Embedding model unavailable (%s); using hashed n-grams",
                    error,
                )

        _EMBEDDER = HashingEmbedder()

        return _EMBEDDER


class SemanticMemory:
    """Embed and store memory text, then search it by similarity."""

    SCHEMA = (
        "CREATE TABLE IF NOT EXISTS semantic_docs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, hash TEXT UNIQUE NOT NULL, "
        "source TEXT NOT NULL, ref TEXT NOT NULL DEFAULT '', "
        "text TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS semantic_vectors ("
        "hash TEXT PRIMARY KEY, model TEXT NOT NULL, dim INTEGER NOT NULL, "
        "vector BLOB NOT NULL)",
        "CREATE TABLE IF NOT EXISTS semantic_meta ("
        "key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    )

    def __init__(self, storage=None, embedder=None, path=None):

        self.storage = storage or Storage()

        self.embedder = embedder or load_embedder()

        self.path = str(path or self.storage.path)

        self.conn = sqlite3.connect(
            self.path, check_same_thread=False, timeout=10.0
        )

        self.conn.row_factory = sqlite3.Row

        for statement in self.SCHEMA:

            self.conn.execute(statement)

        self.conn.commit()

    # ---------------------------------------------------------------- storing

    INDEX_VERSION = "3"

    JUNK = (
        "all ai provider failed",
        "no ai provider",
        "ai provider timed out",
    )

    MIN_WORDS = 3

    MIN_MESSAGE_WORDS = 6

    @classmethod
    def worth_indexing(cls, text, role="") -> bool:

        clean = " ".join((text or "").split())

        if len(clean) < 15:

            return False

        lowered = clean.lower()

        if any(junk in lowered for junk in cls.JUNK):

            return False

        words = [word for word in lowered.replace(":", " ").split() if word]

        if len(words) < cls.MIN_WORDS:

            return False

        # Chit-chat and commands are actions, not knowledge worth recalling.
        if role and len(words) < cls.MIN_MESSAGE_WORDS:

            return False

        return True

    def index(self, text, source="note", ref="") -> bool:

        text = " ".join((text or "").split())

        if len(text) < 3:

            return False

        digest = hashlib.sha1(
            f"{source}:{text}".encode("utf-8")
        ).hexdigest()

        found = self.conn.execute(
            "SELECT 1 FROM semantic_docs WHERE hash = ?", (digest,)
        ).fetchone()

        if found:

            return False

        vector = self.embedder.encode([text])[0]

        self.conn.execute(
            "INSERT INTO semantic_docs (hash, source, ref, text) "
            "VALUES (?, ?, ?, ?)",
            (digest, source, str(ref), text),
        )

        self._save_vector(digest, vector)

        self.conn.commit()

        return True

    def index_many(self, items) -> int:
        """Index (text, source, ref) tuples in one embedding batch."""

        pending = []

        for text, source, ref in items:

            clean = " ".join((text or "").split())

            if len(clean) < 3:

                continue

            digest = hashlib.sha1(
                f"{source}:{clean}".encode("utf-8")
            ).hexdigest()

            found = self.conn.execute(
                "SELECT 1 FROM semantic_docs WHERE hash = ?", (digest,)
            ).fetchone()

            if found:

                continue

            pending.append((digest, source, str(ref), clean))

        if not pending:

            return 0

        vectors = self.embedder.encode([item[3] for item in pending])

        for (digest, source, ref, text), vector in zip(pending, vectors):

            self.conn.execute(
                "INSERT INTO semantic_docs (hash, source, ref, text) "
                "VALUES (?, ?, ?, ?)",
                (digest, source, ref, text),
            )

            self._save_vector(digest, vector)

        self.conn.commit()

        return len(pending)


    def _save_vector(self, digest: str, vector) -> None:

        vector = np.asarray(vector, dtype=np.float32)

        self.conn.execute(
            "INSERT OR REPLACE INTO semantic_vectors "
            "(hash, model, dim, vector) VALUES (?, ?, ?, ?)",
            (digest, self.embedder.name, int(vector.size), vector.tobytes()),
        )

    # --------------------------------------------------------------- indexing

    def migrate(self) -> bool:
        """Wipe an old index once, so junk from earlier versions is gone."""

        if self._meta("index_version") == self.INDEX_VERSION:

            return False

        self.conn.execute("DELETE FROM semantic_vectors")

        self.conn.execute("DELETE FROM semantic_docs")

        self._set_meta("last_message_id", "0")

        self._set_meta("index_version", self.INDEX_VERSION)

        self.conn.commit()

        return True

    def sync(self, max_messages=None) -> int:

        """Index anything new: profile, facts, notes, messages, summaries."""

        added = 0

        try:

            profile = self.storage.get_profile()

        except Exception:

            profile = {}

        for key, value in (profile or {}).items():

            if value:

                added += self.index(
                    f"User profile: {key} is {value}", "profile", key
                )

        for key, value in (self._safe(self.storage.facts) or {}).items():

            if value:

                added += self.index(
                    f"User fact: {key} is {value}", "fact", key
                )

        for note in self._safe(self.storage.notes) or []:

            text = note.get("text") if isinstance(note, dict) else str(note)

            if text:

                added += self.index(text, "note")

        marker = int(self._meta("last_message_id") or 0)

        messages = self._safe(lambda: self.storage.messages_after(marker)) or []

        if max_messages:

            messages = messages[-int(max_messages):]

        for item in messages:

            if self.worth_indexing(item["text"], item.get("role", "")):

                added += self.index(
                    item["text"], "message", item.get("id", "")
                )

            marker = max(marker, int(item.get("id") or 0))

        self._set_meta("last_message_id", str(marker))

        summary = self._safe(self.storage.latest_summary)

        if isinstance(summary, dict):

            summary = summary.get("summary")

        if summary:

            added += self.index(str(summary), "summary")

        self.conn.commit()

        return added

    @staticmethod
    def _safe(call):

        try:

            return call()

        except Exception:

            return None

    def _meta(self, key: str):

        row = self.conn.execute(
            "SELECT value FROM semantic_meta WHERE key = ?", (key,)
        ).fetchone()

        return row["value"] if row else None

    def _set_meta(self, key: str, value: str) -> None:

        self.conn.execute(
            "INSERT OR REPLACE INTO semantic_meta (key, value) VALUES (?, ?)",
            (key, value),
        )

    # --------------------------------------------------------------- searching

    def _rows(self):

        return self.conn.execute(
            "SELECT d.text, d.source, d.ref, v.vector, v.dim "
            "FROM semantic_docs d JOIN semantic_vectors v ON v.hash = d.hash "
            "WHERE v.model = ?",
            (self.embedder.name,),
        ).fetchall()

    def search(self, query, limit=None, min_score=None):

        query = (query or "").strip()

        if not query:

            return []

        limit = int(limit or settings.SEMANTIC_TOP_K)

        threshold = (
            settings.SEMANTIC_MIN_SCORE if min_score is None else min_score
        )

        rows = self._rows()

        if not rows and self._doc_count():

            # The embedding model changed since the last run.
            self.rebuild()

            rows = self._rows()

        if not rows:

            return []

        query_vector = self.embedder.encode([query])[0]

        if int(rows[0]["dim"]) != query_vector.size:

            # The embedding model changed; rebuild with the current one.
            self.rebuild()

            rows = self._rows()

            if not rows:

                return []

        matrix = np.vstack([
            np.frombuffer(row["vector"], dtype=np.float32) for row in rows
        ])

        if matrix.shape[1] != query_vector.size:

            return []

        scores = matrix @ query_vector

        order = np.argsort(-scores)[:limit]

        results = []

        for position in order:

            score = float(scores[position])

            if score < threshold:

                continue

            row = rows[int(position)]

            results.append({
                "text": row["text"],
                "source": row["source"],
                "ref": row["ref"],
                "score": round(score, 3),
            })

        return results

    def _doc_count(self) -> int:

        return self.conn.execute(
            "SELECT COUNT(*) AS count FROM semantic_docs"
        ).fetchone()["count"]

    def rebuild(self) -> int:
        """Re-embed every remembered text with the current model."""

        self.conn.execute(
            "DELETE FROM semantic_vectors WHERE model != ?",
            (self.embedder.name,),
        )

        self.conn.commit()

        docs = self.conn.execute(
            "SELECT hash, text FROM semantic_docs WHERE hash NOT IN "
            "(SELECT hash FROM semantic_vectors)"
        ).fetchall()

        for doc in docs:

            self._save_vector(doc["hash"], self.embedder.encode([doc["text"]])[0])

        self.conn.commit()

        return len(docs)

    def stats(self) -> dict:

        documents = self.conn.execute(
            "SELECT COUNT(*) AS count FROM semantic_docs"
        ).fetchone()["count"]

        return {
            "documents": documents,
            "model": self.embedder.name,
            "dimensions": self.embedder.dim,
        }

    def close(self) -> None:

        try:

            self.conn.close()

        except Exception:

            pass


_SEMANTIC = None
_SEMANTIC_LOCK = threading.Lock()
_READY = threading.Event()
_LAST_SYNC = 0.0
_SYNC_EVERY = 30.0


def get_semantic() -> SemanticMemory:

    global _SEMANTIC

    if _SEMANTIC is not None:

        return _SEMANTIC

    with _SEMANTIC_LOCK:

        if _SEMANTIC is None:

            _SEMANTIC = SemanticMemory()

        return _SEMANTIC


def warm_up() -> bool:
    """Load the model and index what is already remembered."""

    global _LAST_SYNC

    try:

        semantic = get_semantic()

        semantic.migrate()

        semantic.sync()

        _LAST_SYNC = time.monotonic()

        _READY.set()

        log.info(
            "Semantic memory ready: %s (%s docs)",
            semantic.embedder.name,
            semantic.stats()["documents"],
        )

        return True

    except Exception as error:

        log.warning("Semantic memory warm-up failed: %s", error)

        return False


def warm_up_async():

    thread = threading.Thread(
        target=warm_up, name="jarvis-semantic", daemon=True
    )

    thread.start()

    return thread


def search_memory(query, limit=None):
    """Search remembered text by meaning; never blocks a reply on loading."""

    global _LAST_SYNC

    if not _READY.is_set():

        return []

    try:

        semantic = get_semantic()

        if time.monotonic() - _LAST_SYNC > _SYNC_EVERY:

            semantic.sync()

            _LAST_SYNC = time.monotonic()

        return semantic.search(query, limit=limit)

    except Exception as error:

        log.warning("Semantic search failed: %s", error)

        return []


def ready() -> bool:

    return _READY.is_set()
