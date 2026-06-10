"""Metric history and the faithfulness badge: append-only, derived, honest."""

import json
from pathlib import Path

from tessera.eval.harness import EvalReport
from tessera.eval.history import badge_json, load_history, record

_GREEN = EvalReport(
    gold_case_count=7,
    faithfulness=1.0,
    coverage=0.938,
    quality=1.0,
    synthetic_case_count=51,
    synthetic_faithfulness=1.0,
    synthetic_coverage=1.0,
    synthetic_quality=1.0,
)
_BROKEN = EvalReport(gold_case_count=7, faithfulness=0.5, coverage=1.0, quality=1.0)


def test_record_appends_and_never_rewrites(tmp_path: Path) -> None:
    history = tmp_path / "history.jsonl"
    badge = tmp_path / "badge.json"
    record(_GREEN, "first", history, badge, recorded="2026-06-10")
    first_line = history.read_text("utf-8")
    record(_GREEN, "second", history, badge, recorded="2026-06-11")
    content = history.read_text("utf-8")
    assert content.startswith(first_line)  # prior lines untouched
    entries = load_history(history)
    assert [e["note"] for e in entries] == ["first", "second"]
    assert entries[0]["recorded"] == "2026-06-10"


def test_history_entry_carries_both_batteries(tmp_path: Path) -> None:
    history = tmp_path / "history.jsonl"
    record(_GREEN, "note", history, tmp_path / "badge.json", recorded="2026-06-10")
    (entry,) = load_history(history)
    gold = entry["gold"]
    synthetic = entry["synthetic"]
    assert isinstance(gold, dict) and isinstance(synthetic, dict)
    assert gold["cases"] == 7 and gold["faithfulness"] == 1.0
    assert synthetic["cases"] == 51 and synthetic["coverage"] == 1.0


def test_badge_green_while_floor_holds() -> None:
    badge = json.loads(badge_json(_GREEN))
    assert badge == {
        "schemaVersion": 1,
        "label": "faithfulness",
        "message": "1.000",
        "color": "brightgreen",
    }


def test_badge_red_when_floor_broken() -> None:
    badge = json.loads(badge_json(_BROKEN))
    assert badge["color"] == "red"
    assert badge["message"] == "0.500"


def test_committed_badge_matches_committed_history() -> None:
    """The repo's badge must be derivable from its latest history entry — the
    badge can never claim something the journal doesn't."""
    entries = load_history()
    assert entries, "eval/history.jsonl must be seeded"
    latest_gold = entries[-1]["gold"]
    assert isinstance(latest_gold, dict)
    badge = json.loads(
        (Path(__file__).resolve().parents[1] / "eval" / "badge.json").read_text("utf-8")
    )
    assert badge["message"] == f"{latest_gold['faithfulness']:.3f}"
