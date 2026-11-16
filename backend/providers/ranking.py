"""Which free model answers first — measured, not guessed.

``scripts/rank_models.py`` asks every reachable free model a few checkable
questions and writes ``data/model_ranking.json``: quality first, then speed.
This module hands that order to the provider manager and to the vision
fallback. Without a fresh ranking file the static defaults are used.
"""

import json
import logging
import time
from pathlib import Path

logger = logging.getLogger(__name__)

STALE_DAYS = 7

def _file() -> Path:

    from memory.storage import data_dir

    return data_dir() / "model_ranking.json"


def _rows(role: str) -> list:

    try:

        payload = json.loads(_file().read_text(encoding="utf-8"))

    except (OSError, ValueError):

        return []

    measured = float(payload.get("measured") or 0)

    if not measured or time.time() - measured > STALE_DAYS * 86400:

        logger.info("Model ranking is stale; using the static order")

        return []

    return payload.get(role) or []


def models(role: str = "text") -> list:
    """(provider, model) pairs that answered, best first.

    Empty when nothing has been measured: the configured order then stands.
    """

    good = [row for row in _rows(role) if not row.get("error") and row.get("quality")]

    # Share of checks passed first (models are measured with different numbers
    # of them), then the quicker answer; the file may arrive unsorted.
    good.sort(
        key=lambda row: (
            -(float(row.get("quality") or 0) / float(row.get("of") or 5)),
            float(row.get("seconds") or 0),
        )
    )

    return [(row["provider"], row["model"]) for row in good]


def providers(role: str = "text") -> list:
    """Provider names in the order of their best measured model."""

    order = []

    for provider, _model in models(role):

        if provider not in order:

            order.append(provider)

    return order


def broken(role: str = "text") -> list:
    """(provider, model) pairs that failed, so nothing needs to ask them."""

    return [
        (row["provider"], row["model"])
        for row in _rows(role)
        if row.get("error")
    ]
