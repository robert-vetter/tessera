"""The real GitHub Actions battery: the deterministic close (spec 0046) plus the
error-class-synonymy miss the embeddings answer (spec 0056).

Pins RCA over real 11-digit run ids, the ``##[error]``-found error chunks, the
genuine cross-run recurrence — and, deliberately, the **recorded offline miss**:
a question in pure out-of-log vocabulary that lexical BM25 cannot bridge to the
Pages-deploy log, which a semantic index closes (the recorded online close is
spec 0058). Faithfulness stays 1.0 throughout.
"""

from __future__ import annotations

from collections.abc import Sequence

from tessera.devex.knowledge import build_github_actions_graph, build_github_actions_kb
from tessera.devex.rca import explain_failure
from tessera.eval.battery import GoldCase
from tessera.eval.harness import BatteryResult, load_gold_set, run_eval
from tessera.eval.registry import _devex_answer, github_actions_battery
from tessera.platform.vectors import InMemoryVectorStore
from tessera.semantic import SemanticIndex

_PAGES_LOG = "27285174461.failed:chunk1"
_PAGES_RUN = "Run:27285174461"
_RUFF_LOG = "27014662820.failed:chunk1"
_SYNONYMY_QUESTION = "Is the published documentation site unreachable for visitors?"


class _StubEmbeddings:
    """A keyword-axis stand-in for a model that groups the Pages-deploy synonyms
    (the log's literal `HttpError`/`404`/`enabled` and the question's
    `site`/`unreachable`/`visitors`) onto one concept, distinct from the
    ruff-format failure. No network — proves the wiring, not SAP's model."""

    name = "stub"
    _axes = [
        (
            "httperror",
            "not found",
            "404",
            "pages",
            "deploy",
            "enabled",
            "unreachable",
            "unavailable",
            "site",
            "documentation",
            "published",
            "visitors",
        ),
        ("reformat", "ruff", "format"),
    ]

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [1.0 if any(kw in t.lower() for kw in axis) else 0.0 for axis in self._axes]
            for t in texts
        ]


def _stub_index() -> SemanticIndex:
    kb = build_github_actions_kb()
    index = SemanticIndex(provider=_StubEmbeddings(), store=InMemoryVectorStore())
    index.index(kb.records)
    return index


def _synonymy_case() -> GoldCase:
    cases = load_gold_set(github_actions_battery().gold_dir)
    return next(c for c in cases if c.id == "05_pages_synonymy_lookup")


def _gh_result() -> BatteryResult:
    (result,) = run_eval([github_actions_battery()]).batteries
    return result


def test_github_actions_gold_shows_the_recorded_synonymy_miss() -> None:
    """Offline/lexical: the synonymy case is an honest miss (coverage 5/6,
    quality 4/5), faithfulness still gated at 1.0. This sub-1.0 is the milestone's
    point — a real, undeclarable miss the deterministic engine has (the online
    close is recorded in spec 0058)."""
    result = _gh_result()
    assert result.gold_case_count == 5
    assert result.faithfulness == 1.0  # the floor never moves
    assert result.coverage == 5 / 6  # was 1.000 — the recorded synonymy miss
    assert result.quality == 0.8  # 4/5 — the synonymy case refuses offline
    assert result.synthetic_faithfulness == 1.0
    assert result.synthetic_coverage == 1.0


def test_synonymy_case_misses_offline_and_closes_with_a_semantic_index() -> None:
    case = _synonymy_case()
    graph = build_github_actions_graph()
    kb = build_github_actions_kb()

    # Offline (no index → lexical): zero token overlap → principled refusal.
    offline = _devex_answer(case, graph, kb, None)
    assert not offline.is_grounded

    # With a semantic index that groups the synonyms: the case closes by
    # surfacing the failed Docs run (what SAP's model ranks top on the real run;
    # the long error-log chunk dilutes lower — spec 0058's recorded finding).
    closed = _devex_answer(case, graph, kb, _stub_index())
    assert closed.is_grounded
    cited = {rec.id for claim in closed.claims for rec in claim.support}
    assert _PAGES_RUN in cited
    assert "Deploy to GitHub Pages" in closed.render()


def test_semantic_retrieval_precision_no_cross_cause_conflation() -> None:
    """The precision guard: the synonymy query must surface the Pages-deploy
    failure, NOT the unrelated ruff-format failure. Semantics must not trade the
    recall win for a precision loss (ADR 0015)."""
    hits = _stub_index().retrieve(_SYNONYMY_QUESTION, k=5)
    retrieved = {record.id for record, _ in hits}
    assert _PAGES_LOG in retrieved  # recall: the right cause is found
    assert _RUFF_LOG not in retrieved  # precision: the distinct cause is not


def test_rca_finds_real_run_by_numeric_id_and_github_error_marker() -> None:
    graph = build_github_actions_graph()
    answer = explain_failure("Why did run 27014662820 fail?", graph)
    assert answer.is_grounded
    rendered = answer.render()
    # The run row and the ##[error]-marked failed-step log are both surfaced.
    assert "Format check" in rendered
    assert "Would reformat" in rendered
    assert "Process completed with exit code 1" in rendered


def test_rca_detects_real_cross_run_recurrence() -> None:
    graph = build_github_actions_graph()
    answer = explain_failure(
        "Why did run 27285174461 fail, and has this happened before?", graph
    )
    assert answer.is_grounded
    recurrence = [c for c in answer.claims if c.text.startswith("Recurring failure:")]
    assert len(recurrence) == 1
    claim = recurrence[0]
    # The recurrence cites BOTH Pages-deploy runs' logs, sharing the signature.
    assert "Creating Pages deployment failed" in claim.text
    cited = {rec.id for rec in claim.support}
    assert "27285174461.failed:chunk1" in cited
    assert "27284786811.failed:chunk1" in cited


def test_passed_and_unknown_runs_refuse() -> None:
    graph = build_github_actions_graph()
    passed = explain_failure("Why did run 27411838436 fail?", graph)
    assert not passed.is_grounded and "did not fail" in (passed.refusal or "")
    unknown = explain_failure("Why did run 99999999999 fail?", graph)
    assert not unknown.is_grounded and "no run" in (unknown.refusal or "")
