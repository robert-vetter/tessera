"""Synthetic eval cases for the real GitHub Actions battery (ADR 0007 applied).

Deterministic and **data-derived**, exactly like the synthetic DevEx cases:
expectations come from reading the snapshot, never from running the engine. The
anti-tautology point is sharpest here — the expected error support is the set of
log chunks carrying the **real** ``##[error]`` marker, which is *not* how the
deterministic RCA detector currently finds error lines (it keys on a bare
``ERROR``). So the synthetic battery measures the un-planted miss rather than
echoing the engine (spec 0046).
"""

from __future__ import annotations

from tessera.eval.battery import GoldCase
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import KnowledgeBase
from tessera.retrieval import _tokenize

# The real GitHub Actions error marker — what a faithful answer's support should
# cite, independent of how the engine happens to detect it.
GITHUB_ERROR_MARKER = "##[error]"

_MISSING_EVIDENCE_TEMPLATES = (
    "What colour is the sky?",
    "Do we operate a zeppelin fleet?",
)


def _failed_run_error_chunks(graph: KnowledgeGraph, run_id: str) -> list[str]:
    """The run's log chunks that textually carry the real ``##[error]`` marker —
    read from the data, the support a faithful RCA answer should surface."""
    return sorted(
        chunk_id
        for chunk_id in graph.sources_of({run_id}, "log_of")
        if GITHUB_ERROR_MARKER in graph.node(chunk_id).record.text
    )


def _runs(graph: KnowledgeGraph) -> list[Node]:
    return sorted((n for n in graph.nodes if n.kind == "Run"), key=lambda n: n.id)


def generate_cases(graph: KnowledgeGraph, kb: KnowledgeBase) -> list[GoldCase]:
    """Enumerate the GitHub Actions battery from the snapshot graph."""
    cases: list[GoldCase] = []
    node_ids = {n.id for n in graph.nodes}

    for run in _runs(graph):
        run_ref = run.id.removeprefix("Run:")
        question = f"Why did run {run_ref} fail?"
        if run.attr("status") == "failed":
            error_chunks = _failed_run_error_chunks(graph, run.id)
            cases.append(
                GoldCase(
                    id=f"syn_gha_rca_{run_ref}",
                    question=question,
                    engine="rca",
                    kind="answer",
                    expected_support=(run.id, *error_chunks),
                )
            )
        else:
            cases.append(
                GoldCase(
                    id=f"syn_gha_refuse_passed_{run_ref}",
                    question=question,
                    engine="rca",
                    kind="refuse",
                )
            )

    # An unknown numeric run id refuses by name.
    assert "Run:11111111111" not in node_ids
    cases.append(
        GoldCase(
            id="syn_gha_refuse_unknown",
            question="Why did run 11111111111 fail?",
            engine="rca",
            kind="refuse",
        )
    )

    vocabulary = {token for record in kb.records for token in _tokenize(record.text)}
    for index, template in enumerate(_MISSING_EVIDENCE_TEMPLATES, start=1):
        if any(token in vocabulary for token in _tokenize(template)):
            continue
        cases.append(
            GoldCase(
                id=f"syn_gha_refuse_missing_{index}",
                question=template,
                engine="route",
                kind="refuse",
            )
        )

    cases.sort(key=lambda c: c.id)
    return cases
