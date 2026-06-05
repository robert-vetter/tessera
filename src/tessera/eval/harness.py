"""The eval harness: load a gold set, report honestly. Scoring lands in Unit 6.

The shapes here are deliberately minimal. A :class:`GoldCase` currently carries
only the question; expected-answer fields and the faithfulness/coverage/quality
*computation* are defined in Unit 6 (where the faithfulness definition is itself
ADR-worthy), so this scaffold does not pre-empt that design. Until then the
harness loads and counts gold cases and leaves the metrics unset — it never
fabricates a number.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Gold cases live here (one JSON file per case). Empty for now — they arrive with
# the metric in Unit 6. The loader simply finds none and reports honestly.
GOLD_DIR = Path(__file__).resolve().parents[3] / "eval" / "gold"


@dataclass(frozen=True)
class GoldCase:
    """One curated question with a known, fully-sourced answer.

    Minimal on purpose: the expected-answer fields and scoring are defined in
    Unit 6, not here, so this scaffold does not lock in the metric design.
    """

    question: str


@dataclass(frozen=True)
class EvalReport:
    """The outcome of an eval run.

    ``gold_case_count`` is how many curated cases were loaded. The three metrics
    are ``None`` until Unit 6 computes them — never a placeholder number.
    """

    gold_case_count: int
    faithfulness: float | None = None
    coverage: float | None = None
    quality: float | None = None

    @property
    def evaluated(self) -> bool:
        return self.gold_case_count > 0

    def summary(self) -> str:
        if not self.evaluated:
            return (
                "Eval: no gold set evaluated yet — "
                "faithfulness/coverage/quality: n/a (0 gold cases). "
                "The gold set and metrics arrive in Unit 6 (see specs/0011)."
            )
        # Unit 6 fills the scoring; until then we report the count honestly and
        # leave the metrics unset rather than invent values.
        return (
            f"Eval: {self.gold_case_count} gold case(s) loaded; scoring not "
            "implemented yet (Unit 6) — "
            f"faithfulness {_fmt(self.faithfulness)}, "
            f"coverage {_fmt(self.coverage)}, quality {_fmt(self.quality)}."
        )


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.3f}"


def load_gold_set(gold_dir: Path = GOLD_DIR) -> list[GoldCase]:
    """Load every gold case from ``gold_dir`` (one ``*.json`` per case).

    Returns an empty list when the directory is absent or empty — which is the
    expected state until Unit 6 adds the curated cases.
    """
    if not gold_dir.is_dir():
        return []
    cases: list[GoldCase] = []
    for path in sorted(gold_dir.glob("*.json")):
        data = json.loads(path.read_text("utf-8"))
        cases.append(GoldCase(question=str(data["question"])))
    return cases


def run_eval(gold_dir: Path = GOLD_DIR) -> EvalReport:
    """Run the eval and return a report.

    The scaffold loads and counts gold cases; scoring (the faithfulness, coverage,
    and quality metrics) is implemented in Unit 6. It never fabricates a number.
    """
    cases = load_gold_set(gold_dir)
    return EvalReport(gold_case_count=len(cases))
