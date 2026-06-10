"""Metric history and the faithfulness badge: append-only, derived, honest."""

import json
from pathlib import Path

from tessera.eval.harness import BatteryResult, EvalReport
from tessera.eval.history import badge_json, load_history, record

_BUSINESS = BatteryResult(
    name="business",
    gold_case_count=7,
    faithfulness=1.0,
    coverage=0.938,
    quality=1.0,
    synthetic_case_count=51,
    synthetic_faithfulness=1.0,
    synthetic_coverage=1.0,
    synthetic_quality=1.0,
)
_DEVEX = BatteryResult(
    name="devex",
    gold_case_count=6,
    faithfulness=1.0,
    coverage=0.9,
    quality=1.0,
)
_GREEN = EvalReport(batteries=(_BUSINESS, _DEVEX))
_BROKEN = EvalReport(
    batteries=(
        _BUSINESS,
        BatteryResult(
            name="devex", gold_case_count=6, faithfulness=0.5, coverage=1.0, quality=1.0
        ),
    )
)


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


def test_history_entry_carries_every_battery(tmp_path: Path) -> None:
    """Schema v2 (ADR 0009): one line records all measured verticals."""
    history = tmp_path / "history.jsonl"
    record(_GREEN, "note", history, tmp_path / "badge.json", recorded="2026-06-10")
    (entry,) = load_history(history)
    batteries = entry["batteries"]
    assert isinstance(batteries, list)
    by_name = {b["name"]: b for b in batteries}
    assert by_name["business"]["gold"]["cases"] == 7
    assert by_name["business"]["synthetic"]["coverage"] == 1.0
    assert by_name["devex"]["gold"]["faithfulness"] == 1.0


def test_v1_lines_remain_loadable(tmp_path: Path) -> None:
    """Append-only includes the schema's past: the committed Phase 2 lines
    (single gold/synthetic pair) must keep loading next to v2 lines."""
    history = tmp_path / "history.jsonl"
    v1_line = json.dumps(
        {"recorded": "2026-06-09", "note": "phase-2", "gold": {"cases": 7}}
    )
    history.write_text(v1_line + "\n", encoding="utf-8")
    record(_GREEN, "phase-3", history, tmp_path / "badge.json", recorded="2026-06-10")
    entries = load_history(history)
    assert len(entries) == 2
    assert "gold" in entries[0] and "batteries" in entries[1]


def test_badge_is_the_minimum_gold_faithfulness_and_green_iff_floor() -> None:
    badge = json.loads(badge_json(_GREEN))
    assert badge == {
        "schemaVersion": 1,
        "label": "faithfulness",
        "message": "1.000",
        "color": "brightgreen",
    }


def test_badge_red_when_any_battery_breaks_the_floor() -> None:
    badge = json.loads(badge_json(_BROKEN))
    assert badge["color"] == "red"
    assert badge["message"] == "0.500"  # the minimum across batteries


def test_committed_badge_matches_committed_history() -> None:
    """The repo's badge must be derivable from its latest history entry — the
    badge can never claim something the journal doesn't. Handles both line
    shapes (v1 single-pair, v2 batteries)."""
    entries = load_history()
    assert entries, "eval/history.jsonl must be seeded"
    latest = entries[-1]
    if "batteries" in latest:
        batteries = latest["batteries"]
        assert isinstance(batteries, list)
        values = [b["gold"]["faithfulness"] for b in batteries]
        expected = min(values)
    else:
        gold = latest["gold"]
        assert isinstance(gold, dict)
        expected = gold["faithfulness"]
    badge = json.loads(
        (Path(__file__).resolve().parents[1] / "eval" / "badge.json").read_text("utf-8")
    )
    assert badge["message"] == f"{expected:.3f}"
