"""Index real folders so JARVIS can find files by meaning, not by name.

"mera resume kahan hai", "last month ka invoice", "DBMS wale notes" — the
text inside Documents, Downloads and Desktop is extracted, chunked and stored
in the same semantic index the memory uses, so search needs no new query
language. Everything runs locally; no file ever leaves the machine.
"""

import logging
from pathlib import Path

log = logging.getLogger("jarvis.documents")


TEXT_SUFFIXES = {
    ".txt", ".md", ".markdown", ".rst", ".log", ".csv", ".tsv",
    ".json", ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
    ".ini", ".cfg", ".yml", ".yaml", ".toml", ".xml", ".sql", ".env",
}

OFFICE_SUFFIXES = {".pdf", ".docx"}

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist",
    "build", ".next", ".cache", ".pytest_cache", "site-packages",
}

MAX_FILE_BYTES = 8 * 1024 * 1024
CHUNK_CHARS = 700
CHUNK_OVERLAP = 100
MAX_CHUNKS_PER_FILE = 40
MIN_CHUNK_CHARS = 40


def default_folders():
    """The folders a person actually keeps their own files in."""

    home = Path.home()

    candidates = [
        home / "Documents",
        home / "Downloads",
        home / "Desktop",
    ]

    return [str(path) for path in candidates if path.exists()]


def extract_text(path: Path) -> str:
    """Read a file as plain text, including PDF/DOCX when the libs exist."""

    suffix = path.suffix.lower()

    if suffix in TEXT_SUFFIXES:

        return path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":

        try:

            from pypdf import PdfReader

        except Exception as error:

            raise RuntimeError(f"PDF support needs pypdf ({error})") from error

        reader = PdfReader(str(path))

        pages = []

        for page in reader.pages[:60]:

            pages.append(page.extract_text() or "")

        return "\n".join(pages)

    if suffix == ".docx":

        try:

            import docx

        except Exception as error:

            raise RuntimeError(f"DOCX support needs python-docx ({error})") from error

        document = docx.Document(str(path))

        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    return ""


def chunk(text, size: int = CHUNK_CHARS, overlap: int = CHUNK_OVERLAP):
    """Split text into overlapping pieces that end on a sentence when possible."""

    clean = " ".join((text or "").split())

    if not clean:

        return []

    pieces = []
    start = 0

    while start < len(clean) and len(pieces) < MAX_CHUNKS_PER_FILE:

        end = min(len(clean), start + size)

        piece = clean[start:end]

        if end < len(clean):

            cut = max(
                piece.rfind(". "), piece.rfind("? "), piece.rfind("! "),
                piece.rfind("; "),
            )

            if cut > size * 0.5:

                piece = piece[:cut + 1]
                end = start + len(piece)

        piece = piece.strip()

        if len(piece) >= MIN_CHUNK_CHARS:

            pieces.append(piece)

        if end >= len(clean):

            break

        start = max(start + 1, end - overlap)

    return pieces


def _candidates(folders, limit: int, suffixes):

    seen = 0

    for folder in folders:

        root = Path(folder)

        if not root.exists():

            continue

        for path in root.rglob("*"):

            if seen >= limit:

                return

            if not path.is_file():

                continue

            if any(part in SKIP_DIRS for part in path.parts):

                continue

            if path.name.startswith("~$"):

                continue

            if path.suffix.lower() not in suffixes:

                continue

            try:

                size = path.stat().st_size

            except OSError:

                continue

            if size == 0 or size > MAX_FILE_BYTES:

                continue

            seen += 1

            yield path


def index_documents(folders=None, limit: int = 40, semantic=None) -> dict:
    """Extract and index the chosen folders; safe to run again and again."""

    from memory.semantic import get_semantic

    semantic = semantic or get_semantic()

    folders = [str(item) for item in (folders or default_folders())]

    suffixes = TEXT_SUFFIXES | OFFICE_SUFFIXES

    files = 0
    chunks = 0
    skipped = 0
    errors = []

    for path in _candidates(folders, int(limit), suffixes):

        try:

            text = extract_text(path)

        except Exception as error:

            skipped += 1

            errors.append(f"{path.name}: {error}"[:160])

            continue

        pieces = chunk(text)

        if not pieces:

            skipped += 1

            continue

        files += 1

        try:

            chunks += semantic.index_many(
                [(piece, "document", str(path)) for piece in pieces]
            )

        except Exception as error:

            errors.append(f"{path.name}: {error}"[:160])

    log.info("Indexed %s files (%s chunks) from %s", files, chunks, folders)

    return {
        "success": True,
        "folders": folders,
        "files": files,
        "chunks": chunks,
        "skipped": skipped,
        "errors": errors[:5],
        "limit": int(limit),
        **semantic.stats(),
    }


def status(semantic=None) -> dict:
    """How much document text is currently searchable."""

    from memory.semantic import get_semantic

    semantic = semantic or get_semantic()

    row = semantic.conn.execute(
        "SELECT COUNT(*) AS count FROM semantic_docs WHERE source = 'document'"
    ).fetchone()

    return {
        "success": True,
        "documents": int(row["count"] if row else 0),
        "folders": default_folders(),
        "chunks_per_file": MAX_CHUNKS_PER_FILE,
        **semantic.stats(),
    }
