"""Trust metrics over time: an append-only journal and the faithfulness badge.

``eval/history.jsonl`` is the committed, auditable record of how the trust
numbers moved — one JSON object per recorded run, newest last, never rewritten
(like STATUS.md, it is history, not state). ``eval/badge.json`` is a
shields.io endpoint document for the gold faithfulness number; it is green
only while the floor holds.

Recording is a deliberate act (``tessera-eval --record --note "why"``), not a
side effect of every run: the journal should read as a sequence of meaningful
checkpoints, each explaining what changed.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from tessera.eval.harness import EvalReport

EVAL_DIR = Path(__file__).resolve().parents[3] / "eval"
HISTORY_PATH = EVAL_DIR / "history.jsonl"
BADGE_PATH = EVAL_DIR / "badge.json"


def _entry(report: EvalReport, note: str, recorded: str) -> dict[str, object]:
    return {
        "recorded": recorded,
        "note": note,
        "gold": {
            "cases": report.gold_case_count,
            "faithfulness": report.faithfulness,
            "coverage": report.coverage,
            "quality": report.quality,
        },
        "synthetic": {
            "cases": report.synthetic_case_count,
            "faithfulness": report.synthetic_faithfulness,
            "coverage": report.synthetic_coverage,
            "quality": report.synthetic_quality,
        },
    }


def record(
    report: EvalReport,
    note: str,
    history_path: Path = HISTORY_PATH,
    badge_path: Path = BADGE_PATH,
    recorded: str | None = None,
) -> None:
    """Append one history entry and regenerate the badge. Append-only:
    existing lines are never touched."""
    when = recorded or date.today().isoformat()
    with history_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(_entry(report, note, when), ensure_ascii=False) + "\n")
    badge_path.write_text(badge_json(report), encoding="utf-8")


def badge_json(report: EvalReport) -> str:
    """A shields.io endpoint document for the gold faithfulness number."""
    value = report.faithfulness
    message = "n/a" if value is None else f"{value:.3f}"
    color = "brightgreen" if (value is not None and report.floor_holds) else "red"
    return (
        json.dumps(
            {
                "schemaVersion": 1,
                "label": "faithfulness",
                "message": message,
                "color": color,
            }
        )
        + "\n"
    )


def load_history(history_path: Path = HISTORY_PATH) -> list[dict[str, object]]:
    """All recorded entries, oldest first."""
    if not history_path.is_file():
        return []
    entries: list[dict[str, object]] = []
    for line in history_path.read_text("utf-8").splitlines():
        if line.strip():
            loaded = json.loads(line)
            assert isinstance(loaded, dict)
            entries.append(loaded)
    return entries
