import json
from pathlib import Path

from tools import local_intents, reverse_engineer as rea


def test_urls_are_recognised():
    assert rea._as_url("https://www.igloo.inc/") == "https://www.igloo.inc/"
    assert rea._as_url("igloo.inc") == "https://igloo.inc"
    assert rea._as_url("  'www.igloo.inc/portfolio'  ") == "https://www.igloo.inc/portfolio"
    assert rea._as_url("just some words") == ""


def test_reverse_engineer_phrase_finds_the_target():
    intent = local_intents.detect("reverse engineer https://www.igloo.inc/")

    assert intent["tool"] == "reverse_engineer"
    assert intent["arguments"]["target"] == "https://www.igloo.inc/"


def test_reverse_engineer_phrase_works_in_hinglish():
    intent = local_intents.detect("isko reverse engineer karo www.igloo.inc")

    assert intent["arguments"]["target"] == "www.igloo.inc"


def test_a_plain_open_command_is_untouched():
    assert local_intents.detect("open spotify")["tool"] == "open_app"


SAMPLE = {
    "evidence_id": "ev_1234567890abcdef",
    "normalized_result": {
        "route_inventory": {
            "statistics": {"sources_retained": 2},
            "sources": [
                {"url": "https://site.test/assets/app.js", "status": "complete"},
                {"url": "https://site.test/assets/vendor.js", "status": "deadline"},
            ],
            "routes": [],
        },
        "observations": {
            "chunks": {
                "nodes": [
                    {"url": "https://site.test/assets/app.js", "bytes": 2048},
                    {"url": "https://site.test/assets/vendor.js", "bytes": 1024},
                ],
                "edges": [],
            },
            "routes": [{"value": "/portfolio/:project", "mechanism": "property:path"}],
            "endpoints": [{"value": "https://api.site.test/v1/projects"}],
            "source_maps": {"status": "ok", "items": [{"url": "app.js.map"}]},
        },
        "unknowns": [{"kind": "source-unavailable"}],
    },
}


def test_summary_reports_what_was_found(tmp_path):
    text = rea._summarise(SAMPLE, "https://site.test/", tmp_path / "e.json")

    assert "app.js" in text and "complete" in text
    assert "vendor.js" in text and "deadline" in text
    assert "/portfolio/:project" in text
    assert "https://api.site.test/v1/projects" in text
    assert "Source maps: 1" in text
    assert "Unknowns: 1" in text


def test_missing_tools_are_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(rea, "NODE", tmp_path / "node.exe")

    problem = rea._ready()

    assert "Node runtime" in problem

    result = rea.reverse_engineer("https://site.test/")

    assert result["success"] is False
    assert "Node runtime" in result["error"]


def test_a_run_saves_evidence_and_closes_the_browser(monkeypatch, tmp_path):
    monkeypatch.setattr(rea, "_ready", lambda: "")
    monkeypatch.setattr(rea, "_browser", lambda: Path("chrome.exe"))
    monkeypatch.setattr(rea, "_free_port", lambda: 9333)

    launched = {}
    stopped = {}

    def fake_launch(url, port, profile):
        launched["url"] = url

        class Browser:
            pid = 4321

        return Browser()

    def fake_stop(browser):
        stopped["done"] = True

    monkeypatch.setattr(rea, "_launch", fake_launch)
    monkeypatch.setattr(rea, "_wait_for_page", lambda port, host: ("TARGET", "https://site.test/"))
    monkeypatch.setattr(rea, "_run_rea", lambda args, timeout=420: SAMPLE)
    monkeypatch.setattr(rea, "_stop", fake_stop)
    monkeypatch.setattr(rea, "EVIDENCE_DIR", tmp_path / "evidence")

    result = rea.reverse_engineer("site.test")

    assert result["success"] is True
    assert launched["url"] == "https://site.test"
    assert stopped["done"] is True
    assert Path(result["evidence"]).exists()
    assert "app.js" in result["summary"]


def test_a_page_that_never_loads_is_reported(monkeypatch, tmp_path):
    monkeypatch.setattr(rea, "_ready", lambda: "")
    monkeypatch.setattr(rea, "_free_port", lambda: 9334)

    class Browser:
        pid = 4322

    monkeypatch.setattr(rea, "_launch", lambda url, port, profile: Browser())
    monkeypatch.setattr(rea, "_wait_for_page", lambda port, host: None)
    monkeypatch.setattr(rea, "_stop", lambda browser: None)

    result = rea.reverse_engineer("https://site.test/")

    assert result["success"] is False
    assert "did not open" in result["error"]
