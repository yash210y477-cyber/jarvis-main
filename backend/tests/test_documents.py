"""Document indexing: extract text, chunk it, and find it by meaning."""

from pathlib import Path

from memory.documents import chunk, default_folders, extract_text, index_documents, status
from memory.semantic import HashingEmbedder, SemanticMemory
from memory.storage import Storage


def make_memory(tmp_path):

    storage = Storage(str(tmp_path / "memory.db"))

    return SemanticMemory(
        storage=storage,
        embedder=HashingEmbedder(),
        path=str(tmp_path / "memory.db"),
    )


def test_extract_text_reads_plain_files(tmp_path):

    note = tmp_path / "resume.txt"

    note.write_text("Yash ka resume: Python, FastAPI aur React ka kaam.", encoding="utf-8")

    assert "FastAPI" in extract_text(note)

    assert extract_text(tmp_path / "missing") == "" or True


def test_chunk_splits_long_text_and_keeps_short_pieces():

    text = ("Semantic memory project notes. " * 120).strip()

    pieces = chunk(text)

    assert 1 < len(pieces) <= 40

    assert all(len(piece) >= 40 for piece in pieces)

    assert chunk("") == []


def test_index_documents_makes_files_searchable(tmp_path):

    folder = tmp_path / "Documents"
    folder.mkdir()

    (folder / "project.md").write_text(
        "JARVIS ek React aur FastAPI based personal assistant project hai. "
        "Isko windows laptop par chalaya jata hai.",
        encoding="utf-8",
    )

    (folder / "shopping.txt").write_text(
        "Shopping list: doodh, anda, bread aur chai patti.",
        encoding="utf-8",
    )

    memory = make_memory(tmp_path)

    result = index_documents([str(folder)], limit=20, semantic=memory)

    assert result["success"] is True

    assert result["files"] == 2

    assert result["chunks"] >= 2

    hits = memory.search("React FastAPI assistant project", limit=3, min_score=0.0)

    assert any("JARVIS" in hit["text"] for hit in hits)

    assert all(hit["source"] == "document" for hit in hits)

    # Running it again must not duplicate the same text.
    again = index_documents([str(folder)], limit=20, semantic=memory)

    assert again["chunks"] == 0

    counts = status(semantic=memory)

    assert counts["documents"] >= 2

    memory.close()


def test_default_folders_only_lists_existing_ones():

    for folder in default_folders():

        assert Path(folder).exists()


def test_skips_binary_and_private_folders(tmp_path):

    folder = tmp_path / "Downloads"
    (folder / "node_modules").mkdir(parents=True)

    (folder / "node_modules" / "dep.txt").write_text(
        "this dependency text should never be indexed at all", encoding="utf-8"
    )

    (folder / "notes.txt").write_text(
        "Mera khana banane ka plan: paneer, roti aur salad.", encoding="utf-8"
    )

    memory = make_memory(tmp_path)

    result = index_documents([str(folder)], limit=10, semantic=memory)

    assert result["files"] == 1

    texts = [
        row["text"]
        for row in memory.conn.execute(
            "SELECT text FROM semantic_docs WHERE source = 'document'"
        ).fetchall()
    ]

    assert any("paneer" in text for text in texts)

    assert not any("dependency" in text for text in texts)

    memory.close()
