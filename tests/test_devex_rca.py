"""Root-cause analysis: grounded hypotheses, verified claims, honest refusals.

The Unit 4 proof (spec 0029). The strongest test here runs the eval's own
verifier over every claim the RCA path emits — so Unit 8's battery cannot be
surprised: if RCA can say it, the verifier can check it.
"""

from __future__ import annotations

import pytest

from tessera.devex.knowledge import build_devex_graph
from tessera.devex.rca import NO_RUN_REFUSAL, explain_failure
from tessera.eval.metrics import is_supported
from tessera.graph import Edge, KnowledgeGraph, Node
from tessera.grounding import Answer, Claim, EvidenceRecord, Locator, Origin


@pytest.fixture(scope="module")
def graph() -> KnowledgeGraph:
    return build_devex_graph()


def _nodes(graph: KnowledgeGraph) -> dict[str, Node]:
    return {node.id: node for node in graph.nodes}


def _claim_texts(answer: Answer) -> list[str]:
    return [claim.text for claim in answer.claims]


# --- the flagship question -----------------------------------------------------------


def test_r1042_failure_is_explained_and_linked_to_history(
    graph: KnowledgeGraph,
) -> None:
    answer = explain_failure("Why did run R-1042 fail?", graph)
    assert answer.is_grounded
    texts = _claim_texts(answer)

    # The outcome row and the failing log lines, verbatim.
    assert any("Run R-1042" in t and "status failed" in t for t in texts)
    assert any(
        "ERROR payments-service: TimeoutError: connection to payments-db" in t
        for t in texts
    )
    # Recurrence: the same signature in the EARLIER run R-0987's log.
    recurrences = [t for t in texts if t.startswith("Recurring failure:")]
    assert len(recurrences) == 1
    assert "logs/run_R-0987.log" in recurrences[0]
    assert "logs/run_R-1042.log" in recurrences[0]
    # The documented incident, linked and quoted.
    incidents = [t for t in texts if t.startswith("Documented incident:")]
    assert len(incidents) == 1
    assert "tickets.csv" in incidents[0]
    assert any("Ticket DEVEX-187" in t for t in texts)


def test_every_rca_claim_passes_the_faithfulness_verifier(
    graph: KnowledgeGraph,
) -> None:
    nodes = _nodes(graph)
    for question in (
        "Why did run R-1042 fail?",
        "Why did run R-0987 fail?",
        "Why did run R-1031 fail?",
        "Why did run R-1023 fail?",
        "Why did run R-1018 fail?",
        "Why did run R-1012 fail?",
    ):
        answer = explain_failure(question, graph)
        assert answer.is_grounded, question
        for claim in answer.claims:
            assert is_supported(claim, nodes, graph), (question, claim.text)


def test_tampered_recurrence_claim_is_caught(graph: KnowledgeGraph) -> None:
    """The adversarial check (ADR 0005 discipline): take the real recurrence
    claim, alter its quoted signature, and the verifier must reject it."""
    nodes = _nodes(graph)
    answer = explain_failure("Why did run R-1042 fail?", graph)
    real = next(c for c in answer.claims if c.text.startswith("Recurring failure:"))
    assert is_supported(real, nodes, graph)
    tampered = Claim(
        text=real.text.replace("timed out after 30s", "timed out after 31s"),
        support=real.support,
    )
    assert not is_supported(tampered, nodes, graph)


# --- the multi-hop fix chain (spec 0047) ----------------------------------------


def test_r1042_chain_reaches_the_fixing_pr_and_its_diff(
    graph: KnowledgeGraph,
) -> None:
    """The mixed-modality multi-hop in one turn: run row -> log -> prior log ->
    incident ticket -> the PR that resolved it -> the diff that did it."""
    answer = explain_failure("Why did run R-1042 fail, and how was it fixed?", graph)
    texts = _claim_texts(answer)
    # The incident's resolving PR, linked by the exact ticket id, then quoted.
    resolved = [t for t in texts if t.startswith("Resolved by:")]
    assert len(resolved) == 1
    assert '"DEVEX-187"' in resolved[0]
    assert "prs.csv" in resolved[0] and "tickets.csv" in resolved[0]
    assert any("PR PR-198" in t for t in texts)
    # The actual code change — the diff hunk, verbatim (the 10s -> 30s fix).
    assert any("timeout=30" in t and "db_client.py" in t for t in texts)


def test_fix_chain_avoids_the_mispivot(graph: KnowledgeGraph) -> None:
    """DEVEX-187 is fixed by PR-198; PR-201 fixes the *follow-up* DEVEX-204.
    A naive 'any related payments PR' chain would wrongly cite PR-201 and the
    faithfulness verifier would reject it. The exact-id reverse edge cites
    PR-198 only."""
    answer = explain_failure("Why did run R-1042 fail, and how was it fixed?", graph)
    cited = {rec.id for claim in answer.claims for rec in claim.support}
    assert "PR:PR-198" in cited
    assert "PR:PR-201" not in cited


def test_open_incident_has_no_fix_claim(graph: KnowledgeGraph) -> None:
    """R-1031 reaches the OPEN incident DEVEX-231, which no PR resolves: the
    chain stops at the ticket — no 'Resolved by' is invented."""
    texts = _claim_texts(explain_failure("Why did run R-1031 fail?", graph))
    assert any(t.startswith("Documented incident:") for t in texts)
    assert not any(t.startswith("Resolved by:") for t in texts)


# --- recurrence honesty ---------------------------------------------------------


def test_first_occurrence_has_no_recurrence_claim(graph: KnowledgeGraph) -> None:
    """R-1023 is the FIRST search-replica failure: nothing is prior to it,
    so claiming recurrence would be fabrication. Its documented incident
    (DEVEX-231 quotes the signature) still surfaces."""
    texts = _claim_texts(explain_failure("Why did run R-1023 fail?", graph))
    assert not any(t.startswith("Recurring failure:") for t in texts)
    assert any(t.startswith("Documented incident:") for t in texts)


def test_second_occurrence_links_back(graph: KnowledgeGraph) -> None:
    texts = _claim_texts(explain_failure("Why did run R-1031 fail?", graph))
    recurrences = [t for t in texts if t.startswith("Recurring failure:")]
    assert len(recurrences) == 1
    assert "logs/run_R-1023.log" in recurrences[0]


def test_isolated_failures_get_no_history_claims(graph: KnowledgeGraph) -> None:
    """R-1018 (checkout) and R-1012 (auth) each failed once, with no ticket
    quoting their signatures: the answer is the run + its log lines, and
    nothing else — no invented history."""
    for run in ("R-1018", "R-1012"):
        texts = _claim_texts(explain_failure(f"Why did run {run} fail?", graph))
        assert not any(t.startswith("Recurring failure:") for t in texts), run
        assert not any(t.startswith("Documented incident:") for t in texts), run
        assert any("ERROR" in t for t in texts), run


# --- refusals -------------------------------------------------------------------


def test_passed_run_is_a_refused_premise(graph: KnowledgeGraph) -> None:
    answer = explain_failure("Why did run R-1041 fail?", graph)
    assert not answer.is_grounded
    assert answer.refusal is not None
    assert "did not fail" in answer.refusal


def test_unknown_run_is_refused_by_name(graph: KnowledgeGraph) -> None:
    answer = explain_failure("Why did run R-9999 fail?", graph)
    assert not answer.is_grounded
    assert answer.refusal is not None
    assert "R-9999" in answer.refusal


def test_question_without_a_run_is_refused(graph: KnowledgeGraph) -> None:
    answer = explain_failure("Why did the pipeline fail?", graph)
    assert answer.refusal == NO_RUN_REFUSAL


# --- foreign-log shapes: signature sharpness + anchor correctness (spec 0126) --------
#
# The M18 `smoke` run on mkdocs/mkdocs surfaced a real claims-supported FAIL:
# the recurrence claim anchored `error_chunks[0]`, which on that log is an
# error-marked chunk carrying no parseable error line — the shared-fragment
# verifier rightly rejected the citation. These fixtures pin that foreign
# shape (and the generic-trailer preference) WITHOUT committing foreign data
# (ADR 0028): synthetic graphs, same code path, verified by the eval's own
# `is_supported`.


def _log_record(run: str, chunk: int, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=f"Chunk:{run}/{chunk}",
        origin=Origin(
            source=f"logs/run_{run}.log",
            locator=Locator(
                kind="log-span",
                parts=(("lines", "1-3"), ("chunk", str(chunk))),
            ),
            ingested_at="2026-07-03",
        ),
        text=text,
    )


def _run_record(run: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=f"Run:{run}",
        origin=Origin(
            source="runs.csv",
            locator=Locator.table_row("runs", 1),
            ingested_at="2026-07-03",
        ),
        text=f"Run {run}: workflow ci, status failed.",
    )


def _foreign_graph(
    current_chunks: list[str], prior_chunks: list[str]
) -> KnowledgeGraph:
    """Two failed runs (R-9001 now, R-9000 earlier) with the given log texts."""
    graph = KnowledgeGraph()
    for run, started, texts in (
        ("R-9000", "2026-07-01T10:00:00Z", prior_chunks),
        ("R-9001", "2026-07-02T10:00:00Z", current_chunks),
    ):
        graph.add_node(
            Node(
                record=_run_record(run),
                kind="Run",
                attributes=(("status", "failed"), ("started", started)),
            )
        )
        for index, text in enumerate(texts):
            record = _log_record(run, index, text)
            graph.add_node(Node(record=record, kind="document"))
            graph.add_edge(Edge(src=record.id, dst=f"Run:{run}", relation="log_of"))
    return graph


_TRAILER = "##[error]Process completed with exit code 1."


def test_anchor_is_the_signature_bearing_chunk_not_blindly_the_first() -> None:
    """The mkdocs shape: chunk 0 is error-marked but unparseable (a plain
    'ERROR - …' diagnostic); the only parseable line is the trailer in chunk
    1. The recurrence claim must cite the chunk that CONTAINS the signature —
    and must pass the very verifier that failed on the old anchor."""
    graph = _foreign_graph(
        current_chunks=[
            "ERROR - Doc file 'a.md' contains an absolute link",
            _TRAILER,
        ],
        prior_chunks=[_TRAILER],
    )
    answer = explain_failure("Why did run R-9001 fail?", graph)
    recurrences = [
        claim for claim in answer.claims if claim.text.startswith("Recurring failure:")
    ]
    assert len(recurrences) == 1
    (claim,) = recurrences
    cited = {record.id for record in claim.support}
    assert "Chunk:R-9001/1" in cited  # the signature's own chunk
    assert "Chunk:R-9001/0" not in cited  # the old, wrong anchor
    nodes = {node.id: node for node in graph.nodes}
    assert is_supported(claim, nodes, graph)


def test_sharper_signature_beats_the_generic_trailer() -> None:
    """When any non-generic error line exists, it is the signature — the
    information-free exit-code trailer no longer wins just by coming first."""
    sharper = "##[error]strict mode: 4 warnings raised"
    graph = _foreign_graph(
        current_chunks=[_TRAILER, sharper],
        prior_chunks=[f"{_TRAILER}\n{sharper}"],
    )
    answer = explain_failure("Why did run R-9001 fail?", graph)
    recurrences = [
        claim for claim in answer.claims if claim.text.startswith("Recurring failure:")
    ]
    assert len(recurrences) == 1
    (claim,) = recurrences
    assert '"strict mode: 4 warnings raised"' in claim.text
    assert "exit code" not in claim.text
    cited = {record.id for record in claim.support}
    assert "Chunk:R-9001/1" in cited
    nodes = {node.id: node for node in graph.nodes}
    assert is_supported(claim, nodes, graph)


def test_trailer_only_log_keeps_the_trailer_signature() -> None:
    """A log with nothing sharper still yields the (weak) trailer signature —
    the recurrence claim is true and verified; flagging its weakness stays
    `tessera smoke`'s job (spec 0119), unchanged."""
    graph = _foreign_graph(current_chunks=[_TRAILER], prior_chunks=[_TRAILER])
    answer = explain_failure("Why did run R-9001 fail?", graph)
    recurrences = [
        claim for claim in answer.claims if claim.text.startswith("Recurring failure:")
    ]
    assert len(recurrences) == 1
    (claim,) = recurrences
    assert '"Process completed with exit code 1."' in claim.text
    nodes = {node.id: node for node in graph.nodes}
    assert is_supported(claim, nodes, graph)


def test_unverifiable_sharp_line_never_displaces_a_verifiable_signature() -> None:
    """Review finding (MAJOR): a sharper line the shared-fragment grammar
    cannot check — here one containing a double quote — must not be selected;
    the verifiable (generic) trailer stays the signature and the claim still
    passes the verifier. The old preference picked the quoted line and the
    claim failed our own check."""
    quoted = '##[error]Missing config key "docs_dir"'
    graph = _foreign_graph(
        current_chunks=[_TRAILER, quoted],
        prior_chunks=[f"{_TRAILER}\n{quoted}"],
    )
    answer = explain_failure("Why did run R-9001 fail?", graph)
    recurrences = [
        claim for claim in answer.claims if claim.text.startswith("Recurring failure:")
    ]
    assert len(recurrences) == 1
    (claim,) = recurrences
    assert '"Process completed with exit code 1."' in claim.text
    assert "docs_dir" not in claim.text
    nodes = {node.id: node for node in graph.nodes}
    assert is_supported(claim, nodes, graph)


def test_no_verifiable_candidate_means_no_recurrence_claim() -> None:
    """A log whose only error lines normalize to nothing (non-Latin or
    punctuation-only) yields NO recurrence/incident claim — never a claim our
    own verifier would reject (ADR 0005 / spec 0029). The verbatim error
    chunks still speak for themselves."""
    graph = _foreign_graph(
        current_chunks=["##[error]テストが失敗しました", "##[error]!!!"],
        prior_chunks=["##[error]テストが失敗しました"],
    )
    answer = explain_failure("Why did run R-9001 fail?", graph)
    assert answer.is_grounded  # run row + verbatim error chunks
    texts = _claim_texts(answer)
    assert not any(t.startswith("Recurring failure:") for t in texts)
    assert any("テストが失敗しました" in t for t in texts)  # still quoted verbatim
    nodes = {node.id: node for node in graph.nodes}
    assert all(is_supported(c, nodes, graph) for c in answer.claims)


def test_whitespace_only_error_marker_is_not_a_candidate() -> None:
    """Review finding: a bare '##[error]   ' remainder must not become the
    (empty) signature — empty "appears" everywhere and verifies nowhere."""
    graph = _foreign_graph(
        current_chunks=["##[error]   ", _TRAILER],
        prior_chunks=[_TRAILER],
    )
    answer = explain_failure("Why did run R-9001 fail?", graph)
    recurrences = [
        claim for claim in answer.claims if claim.text.startswith("Recurring failure:")
    ]
    assert len(recurrences) == 1
    assert '"Process completed with exit code 1."' in recurrences[0].text
    nodes = {node.id: node for node in graph.nodes}
    assert is_supported(recurrences[0], nodes, graph)


def test_negative_exit_code_trailer_counts_as_generic() -> None:
    """Windows runners produce negative exit codes; a negative trailer is the
    same weak signal and must not displace a sharper line (review finding)."""
    negative = "##[error]Process completed with exit code -1073741819."
    sharper = "##[error]Access violation in worker"
    graph = _foreign_graph(
        current_chunks=[negative, sharper],
        prior_chunks=[f"{negative}\n{sharper}"],
    )
    answer = explain_failure("Why did run R-9001 fail?", graph)
    recurrences = [
        claim for claim in answer.claims if claim.text.startswith("Recurring failure:")
    ]
    assert len(recurrences) == 1
    assert '"Access violation in worker"' in recurrences[0].text
    nodes = {node.id: node for node in graph.nodes}
    assert is_supported(recurrences[0], nodes, graph)


def test_anchor_is_the_extraction_chunk_not_an_incidental_earlier_match() -> None:
    """An earlier error-marked chunk that merely QUOTES the signature text
    (e.g. a diagnostic echoing the message) must not become the citation; the
    anchor is the chunk the line was parsed from."""
    graph = _foreign_graph(
        current_chunks=[
            # Error-marked (contains 'ERROR'), unparseable, and incidentally
            # containing the trailer text as prose.
            "ERROR - context: the previous attempt ended with "
            "Process completed with exit code 1. earlier today",
            _TRAILER,
        ],
        prior_chunks=[_TRAILER],
    )
    answer = explain_failure("Why did run R-9001 fail?", graph)
    recurrences = [
        claim for claim in answer.claims if claim.text.startswith("Recurring failure:")
    ]
    assert len(recurrences) == 1
    cited = {record.id for record in recurrences[0].support}
    assert "Chunk:R-9001/1" in cited  # the extraction chunk
    assert "Chunk:R-9001/0" not in cited  # the incidental earlier match
    nodes = {node.id: node for node in graph.nodes}
    assert is_supported(recurrences[0], nodes, graph)
