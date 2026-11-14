"""Reverse engineer a website with REA (rea-agents).

A URL is opened in a throwaway headless Chrome with remote debugging on, REA
attaches over CDP, captures the page's scripts and returns static evidence:
bundles, chunk edges, route candidates, endpoint candidates and source maps.
Everything runs read-only; the browser closes when the analysis finishes.

REA needs Node 22.23.4+/24.22.1+ and a published CLI build, so the project keeps
its own copy under backend/data/tools instead of touching the system install.
"""

import json
import logging
import re
import socket
import subprocess
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BACKEND = Path(__file__).resolve().parents[1]

TOOLS = BACKEND / "data" / "tools"

NODE = TOOLS / "node-v24.22.3-win-x64" / "node.exe"

CLI = TOOLS / "rea" / "node_modules" / "rea-agents" / "scripts" / "rea.mjs"

EVIDENCE_DIR = BACKEND / "data" / "rea"

BROWSERS = (
    Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
    Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
)

ANALYSIS_ARGS = [
    "--format", "json",
    "--observation-ms", "1500",
    "--analysis-timeout-ms", "180000",
    "--total-analysis-timeout-ms", "420000",
    "--fetch-source-maps",
]


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:

        sock.bind(("127.0.0.1", 0))

        return sock.getsockname()[1]


def _browser() -> Path:
    for path in BROWSERS:

        if path.exists():

            return path

    raise FileNotFoundError("Chrome or Edge was not found on this computer.")


def _ready() -> str:
    """Empty string when REA can run, otherwise what is missing."""

    if not NODE.exists():

        return "The bundled Node runtime is missing (backend/data/tools)."

    if not CLI.exists():

        return "REA is not installed (backend/data/tools/rea)."

    try:

        _browser()

    except FileNotFoundError as error:

        return str(error)

    return ""


def _launch(url: str, port: int, profile: Path):
    profile.mkdir(parents=True, exist_ok=True)

    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    return subprocess.Popen(
        [
            str(_browser()),
            "--headless=new",
            f"--remote-debugging-port={port}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-gpu",
            "--disable-extensions",
            url,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )


def _wait_for_page(port: int, host: str, timeout: float = 30.0):
    """(target_id, url) of the page that loaded, or None."""

    deadline = time.time() + timeout

    while time.time() < deadline:

        try:

            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json/list", timeout=3
            ) as response:

                pages = json.loads(response.read().decode("utf-8"))

        except Exception:

            time.sleep(0.5)

            continue

        for page in pages:

            if page.get("type") != "page":

                continue

            page_host = urlparse(page.get("url") or "").netloc.lower()

            if host and host not in page_host:

                continue

            return page.get("id"), page.get("url")

        time.sleep(0.5)

    return None


def _stop(process):

    try:

        process.terminate()

        process.wait(timeout=8)

    except Exception:

        pass

    try:

        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )

    except Exception:

        pass


def _run_rea(args, timeout=420) -> dict:

    completed = subprocess.run(
        [str(NODE), str(CLI), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    if completed.returncode != 0:

        message = (completed.stderr or completed.stdout or "").strip()

        raise RuntimeError(message[:600] or "REA failed without a message.")

    text = (completed.stdout or "").strip()

    if not text:

        raise RuntimeError("REA returned no output.")

    return json.loads(text)


def _as_url(target: str) -> str:
    target = (target or "").strip().strip("\"'<>")

    if not target:

        return ""

    if re.match(r"^https?://", target, re.I):

        return target

    if re.match(r"^[\w-]+(\.[\w-]+)+(/.*)?$", target):

        return "https://" + target

    return ""


def _entries(value):
    """REA nests some observations as {items: [...]} or {nodes: [...], edges: [...]}."""

    if isinstance(value, dict):

        for key in ("items", "nodes", "entries", "list"):

            if isinstance(value.get(key), list):

                return value[key]

        return []

    return value or []


def _text(value, *keys) -> str:
    if isinstance(value, str):

        return value

    if isinstance(value, dict):

        for key in keys:

            if value.get(key):

                return str(value[key])

        return json.dumps(value)[:160]

    return str(value)[:160]


def _summarise(payload: dict, target: str, evidence_path: Path) -> str:
    """A short, readable report of what REA found."""

    result = payload.get("normalized_result") or {}

    inventory = result.get("route_inventory") or {}

    observations = result.get("observations") or {}

    statistics = inventory.get("statistics") or {}

    sources = inventory.get("sources") or []

    lines = [f"REA analysed **{target}**"]

    if payload.get("evidence_id"):

        lines.append(f"evidence: `{payload['evidence_id'][:24]}…`")

    lines.append("")

    lines.append(f"Scripts: {statistics.get('sources_retained', len(sources))} captured")

    for source in sources[:8]:

        name = (source.get("url") or source.get("path") or "inline").split("/")[-1]

        lines.append(f"- `{name}` — {source.get('status') or 'unknown'}")

    chunks = _entries(observations.get("chunks"))

    if chunks:

        lines.append("")

        lines.append(f"Chunks: {len(chunks)}")

        for chunk in chunks[:5]:

            size = chunk.get("bytes") if isinstance(chunk, dict) else None

            label = _text(chunk, "id", "name", "url", "target")

            lines.append(
                f"- `{label.split('/')[-1]}`" + (f" ({size:,} bytes)" if size else "")
            )

    routes = _entries(observations.get("routes")) or _entries(inventory.get("routes"))

    if routes:

        lines.append("")

        lines.append(f"Route candidates: {len(routes)}")

        for route in routes[:8]:

            lines.append(f"- `{_text(route, 'pattern', 'path', 'route', 'value')}`")

    endpoints = _entries(observations.get("endpoints"))

    if endpoints:

        lines.append("")

        lines.append(f"Endpoint candidates: {len(endpoints)}")

        for endpoint in endpoints[:8]:

            lines.append(f"- `{_text(endpoint, 'url', 'value', 'endpoint')}`")

    source_maps = _entries(observations.get("source_maps"))

    if source_maps:

        lines.append("")

        lines.append(f"Source maps: {len(source_maps)}")

    unknowns = result.get("unknowns") or []

    if unknowns:

        lines.append("")

        lines.append(f"Unknowns: {len(unknowns)} (see the evidence file)")

    lines.append("")

    lines.append(f"Evidence saved to `{evidence_path}`")

    return "\n".join(lines)


def reverse_engineer(target: str) -> dict:
    """Reverse engineer a website URL (or a local file with REA's analyzers)."""

    problem = _ready()

    if problem:

        return {"success": False, "error": problem}

    url = _as_url(target)

    if not url:

        path = Path(target).expanduser()

        if not path.exists():

            return {
                "success": False,
                "error": "Give a website URL or a local file/folder to analyse.",
            }

        try:

            payload = _run_rea(["analyze", str(path), "--format", "json"])

        except Exception as error:

            return {"success": False, "error": str(error)}

        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

        saved = EVIDENCE_DIR / f"file-{datetime.now():%Y%m%d-%H%M%S}.json"

        saved.write_text(json.dumps(payload, indent=1)[:4_000_000], encoding="utf-8")

        return {
            "success": True,
            "target": str(path),
            "summary": _summarise(payload, str(path), saved),
            "evidence": str(saved),
        }

    host = urlparse(url).netloc.lower().split(":")[0]

    port = _free_port()

    profile = BACKEND / "data" / "rea-profile" / f"run-{int(time.time())}"

    browser = _launch(url, port, profile)

    try:

        found = _wait_for_page(port, host)

        if not found:

            return {
                "success": False,
                "error": f"The page did not open in the analysis browser ({url}).",
            }

        target_id, page_url = found

        payload = _run_rea(
            [
                "analyze-web-bundle",
                f"http://127.0.0.1:{port}",
                target_id,
                *ANALYSIS_ARGS,
            ]
        )

    except Exception as error:

        logger.info("REA failed for %s: %s", url, error)

        return {"success": False, "target": url, "error": str(error)[:600]}

    finally:

        _stop(browser)

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-") or "site"

    saved = EVIDENCE_DIR / f"{slug}-{datetime.now():%Y%m%d-%H%M%S}.json"

    saved.write_text(json.dumps(payload, indent=1), encoding="utf-8")

    try:

        summary = _summarise(payload, page_url or url, saved)

    except Exception as error:

        logger.info("REA summary failed: %s", error)

        summary = (
            f"REA finished on **{page_url or url}**.\n\n"
            f"Evidence saved to `{saved}`"
        )

    risk = payload.get("risk") or {}

    return {
        "success": True,
        "target": url,
        "page": page_url,
        "evidence_id": payload.get("evidence_id"),
        "summary": summary,
        "evidence": str(saved),
        "risk": risk,
    }
