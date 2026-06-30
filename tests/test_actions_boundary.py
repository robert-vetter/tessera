"""The recorded measurement: the trust contract survives the *action* boundary.

Milestone 12 Unit 5 (spec 0091). The action-level analogue of ``tests/test_boundary``:
over cases derived from the data (every failed run yields an incident; every PR a PR
summary — anti-tautology, ADR 0007), three properties are gated in CI.

1. Every drafted action is **field-grounded and lossless**: each non-title field mirrors
   exactly one grounded claim (same value, same support ids, and the *same* verifier
   verdict, recomputed independently here — not read from the proposal); the optional
   title is a verbatim fragment of a grounded claim's own evidence and is verified.
2. **Faithfulness is 1.0 across the action boundary**: every field of every derived case
   is verifier-passing. A drafter that fabricated or over-claimed a field fails this.
3. A refusal — passed/unknown run, out-of-scope, incompatible route, wrong domain — is
   **carried, never drafted**: the proposal refuses with no fields.

Offline and pure-stdlib (it drives ``ground`` + ``draft_action``, no SDK), so it runs in
the gate. Faithfulness stays the single hard floor; this property is *pinned*, not a new
gated metric (the M11 pattern).
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from tessera.agent.actions import draft_action
from tessera.agent.grounded import ground
from tessera.devex.knowledge import build_devex_graph, build_github_actions_graph
from tessera.graph import KnowledgeGraph

BuildGraph = Callable[[], KnowledgeGraph]


def _failed_runs(build: BuildGraph) -> list[str]:
    return sorted(
        node.record.id.removeprefix("Run:")
        for node in build().nodes
        if node.kind == "Run" and node.attr("status") == "failed"
    )


def _prs(build: BuildGraph) -> list[str]:
    return sorted(
        node.record.id.removeprefix("PR:")
        for node in build().nodes
        if node.kind == "PR"
    )


def _action_cases() -> Iterator[tuple[str, str, str]]:
    """(action_kind, domain, question) for every groundable action the corpus supports:
    an incident per failed run (devex + the real github_actions connector), a PR summary
    per devex PR. Derived from the graphs, so the measurement widens with the data."""
    for run_id in _failed_runs(build_devex_graph):
        yield "incident", "devex", f"Why did run {run_id} fail?"
    for run_id in _failed_runs(build_github_actions_graph):
        yield "incident", "github_actions", f"Why did run {run_id} fail?"
    for pr_id in _prs(build_devex_graph):
        yield "pr_summary", "devex", f"What does {pr_id} change?"


def test_every_drafted_action_is_field_grounded_and_lossless() -> None:
    """For every derived case the proposal is grounded and all_grounded, and its fields
    are a lossless projection of the grounding: each non-title field is exactly one
    grounded claim (value, support ids, and the verdict recomputed from the grounding),
    and the title is a verbatim fragment of grounded evidence — nothing added, dropped,
    or relabeled into a false verdict."""
    cases = list(_action_cases())
    assert cases  # the corpus supports at least one groundable action
    for kind, domain, question in cases:
        proposal = draft_action(kind, domain, question)
        grounding = ground(domain, question)
        tag = f"{kind}/{domain}: {question}"

        assert proposal.grounded and not proposal.refused, tag
        assert proposal.all_grounded, tag  # every field verifier-passing
        assert proposal.requires_approval is True and proposal.executed is False, tag

        # Non-title fields project the grounded claims one-for-one, in order.
        non_title = [f for f in proposal.fields if f.name != "title"]
        assert len(non_title) == len(grounding.claims), tag
        for field, claim in zip(non_title, grounding.claims, strict=True):
            assert field.value == claim.text, tag
            assert {e.id for e in field.support} == {e.id for e in claim.support}, tag
            # The verdict equals the grounding's own verdict — and faithfulness is 1.0.
            assert field.verified == claim.verified, tag
            assert field.verified, tag

        # The optional title is a verbatim fragment of some grounded claim's evidence.
        claim_texts = {c.text for c in grounding.claims}
        evidence_texts = [e.text for c in grounding.claims for e in c.support]
        for title in (f for f in proposal.fields if f.name == "title"):
            assert title.value in claim_texts or any(
                title.value in ev for ev in evidence_texts
            ), tag
            assert title.verified, tag


def test_faithfulness_is_one_across_the_action_boundary() -> None:
    """The headline gated property: counted over every field of every derived case,
    every drafted field is verifier-passing — faithfulness 1.0 across the boundary."""
    total = 0
    verified = 0
    for kind, domain, question in _action_cases():
        proposal = draft_action(kind, domain, question)
        assert not proposal.refused, f"{kind}/{domain}: {question}"
        for field in proposal.fields:
            total += 1
            verified += 1 if field.verified else 0
    assert total > 0
    assert verified == total  # faithfulness == 1.0 across the action boundary


def test_a_refusal_is_carried_never_drafted_across_the_boundary() -> None:
    """No action is ever proposed on ungrounded ground: a run that passed, an unknown
    run (synthetic and real), an out-of-scope question, an incompatible route, and a
    wrong domain each yield a carried refusal with no fields."""
    passed_run = next(
        node.record.id.removeprefix("Run:")
        for node in build_devex_graph().nodes
        if node.kind == "Run" and node.attr("status") == "passed"
    )
    cases = [
        ("incident", "devex", f"Why did run {passed_run} fail?"),  # it passed
        ("incident", "devex", "Why did run R-9999 fail?"),  # unknown synthetic run
        ("incident", "devex", "What is the capital of France?"),  # out of scope
        (
            "incident",
            "github_actions",
            "Why did run 99999999 fail?",
        ),  # unknown real run
        (
            "incident",
            "devex",
            "What does PR-201 change?",
        ),  # incompatible route (summary)
        ("pr_summary", "github_actions", "What does PR-201 change?"),  # wrong domain
    ]
    for kind, domain, question in cases:
        proposal = draft_action(kind, domain, question)
        tag = f"{kind}/{domain}: {question}"
        assert proposal.refused and not proposal.grounded, tag
        assert proposal.fields == (), tag
        assert not proposal.all_grounded, tag
        assert proposal.refusal, tag


def test_adr_0005_0006_not_forced_at_the_action_boundary() -> None:
    """ADR 0005 (LLM-judge) / 0006 (semantic routing) re-examined at the action boundary
    and recorded NOT forced: every drafted field's verdict is the same structural
    ``is_supported`` check the eval gates on, so no semantic judge was needed across the
    boundary (0005 unforced); and drafting is deterministic selection/templating over
    verifier-passing claims — not LLM generation, not semantic routing (0006 unforced).
    A documentation pin — revisited if a future measured case forces a trigger."""
    proposal = draft_action(
        "incident", "devex", "Why did run R-1042 fail, and has this happened before?"
    )
    # The structural verifier sufficed to ground every field across the boundary.
    assert proposal.all_grounded
