"""The recorded measurement: the trust contract survives the protocol boundary.

Milestone 11 Unit 5 (spec 0085). The headline is a *property*, gated in CI: over
every gold case in every battery, projecting the engine's answer through the
agent-facing boundary preserves it exactly — same claims, same support, same
verifier verdicts — and faithfulness stays 1.0. A boundary that dropped, added, or
altered a claim, or turned a refusal into an answer, would fail these.

Two router-vs-engine dispositional divergences are pinned explicitly and explained
(neither is a faithfulness breach); a *third* would fail the test loudly.
"""

from __future__ import annotations

from collections.abc import Iterator

from tessera.agent.grounded import ground, serialize_answer
from tessera.eval.battery import Battery, GoldCase
from tessera.eval.harness import load_gold_set
from tessera.eval.metrics import is_supported
from tessera.eval.registry import batteries
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import KnowledgeBase
from tessera.routing import Route


def _gold_cases() -> Iterator[tuple[Battery, KnowledgeGraph, KnowledgeBase, GoldCase]]:
    """(battery, graph, kb, case) for every committed gold case in every battery."""
    for battery in batteries():
        graph = battery.build_graph()
        kb = battery.build_kb()
        for case in load_gold_set(battery.gold_dir):
            yield battery, graph, kb, case


def test_boundary_serialization_is_lossless_for_every_gold_case() -> None:
    """The projection adds and drops nothing: the GroundedResult mirrors the
    engine's Answer claim-for-claim, support-id-for-support-id, verdict-for-verdict;
    a refusal projects to an explicit refusal."""
    for battery, graph, kb, case in _gold_cases():
        answer = battery.answer(case, graph, kb, None)  # offline (index=None)
        result = serialize_answer(
            answer,
            graph,
            battery.claim_shapes,
            domain=battery.name,
            question=case.question,
            route=Route(kind=case.engine, reason="eval engine dispatch"),
        )
        # Disposition preserved.
        assert result.grounded == answer.is_grounded, case.id
        assert result.refused == (not answer.is_grounded), case.id
        if not answer.is_grounded:
            assert result.refusal, case.id
            assert result.claims == (), case.id
            continue
        # Claim texts preserved, in order.
        assert [c.text for c in result.claims] == [c.text for c in answer.claims], (
            case.id
        )
        # Support ids preserved per claim (as sets — order is sorted at the boundary).
        nodes: dict[str, Node] = {n.id: n for n in graph.nodes}
        for gclaim, aclaim in zip(result.claims, answer.claims, strict=True):
            assert {e.id for e in gclaim.support} == {r.id for r in aclaim.support}, (
                case.id
            )
            # The verdict equals the independent verifier — not a hardcoded True.
            assert gclaim.verified == is_supported(
                aclaim, nodes, graph, battery.claim_shapes
            ), case.id


def test_faithfulness_is_one_across_the_boundary() -> None:
    """The gated floor, preserved through the projection: every claim of every gold
    case is verifier-supported once it has crossed the boundary."""
    total = 0
    verified = 0
    for battery, graph, kb, case in _gold_cases():
        answer = battery.answer(case, graph, kb, None)
        result = serialize_answer(
            answer,
            graph,
            battery.claim_shapes,
            domain=battery.name,
            question=case.question,
            route=Route(kind=case.engine, reason="eval engine dispatch"),
        )
        for claim in result.claims:
            total += 1
            verified += 1 if claim.verified else 0
    assert total > 0
    assert verified == total  # faithfulness == 1.0 across the boundary


# The pinned router-vs-engine divergence (spec 0085). The agent calls the
# production router (ground), not the eval's per-case engine dispatch; this gold
# case routes differently. It is not a faithfulness breach (all_verified holds) and
# is explained. A NEW divergence — or this one changing — fails
# test_router_path_disposition_matches_gold_except_pinned below.
#
# Milestone 12 Unit 2 (spec 0088) CLOSED the second former divergence: the bare
# ambiguous term "Logistik" (business/05) now routes to the compose path and refuses
# as ambiguous (the router defers to compose's resolver), so its disposition matches
# the gold kind and it is no longer pinned.
_EXPECTED_ROUTER_DIVERGENCES = {
    # Offline synonymy miss: zero lexical overlap with the 404 lines; only
    # embeddings bridge it (M6/M7, online). The agent layer is offline/lexical
    # (ADR 0022), so it refuses — exactly as offline CI does (coverage 0.833).
    ("github_actions", "05_pages_synonymy_lookup"): "refused",
}


def test_router_path_disposition_matches_gold_except_pinned() -> None:
    """The agent-facing router path: every gold case stays faithful (all_verified),
    and its grounded/refused disposition matches the gold kind except the two pinned,
    explained divergences."""
    for battery, _graph, _kb, case in _gold_cases():
        result = ground(battery.name, case.question)
        # Faithfulness holds on the router path for every gold case.
        assert result.all_verified, f"{battery.name}/{case.id} not all_verified"

        disposition = "grounded" if result.grounded else "refused"
        pinned = _EXPECTED_ROUTER_DIVERGENCES.get((battery.name, case.id))
        if pinned is not None:
            assert disposition == pinned, (
                f"{battery.name}/{case.id}: pinned divergence expected {pinned}, "
                f"got {disposition}"
            )
            continue
        expected = "grounded" if case.kind == "answer" else "refused"
        assert disposition == expected, (
            f"{battery.name}/{case.id}: expected {expected}, got {disposition} "
            f"(a new router-vs-engine divergence — record it in spec 0085)"
        )


def test_adr_0005_0006_triggers_not_forced_by_the_boundary() -> None:
    """ADR 0005 (LLM-judge) / 0006 (semantic routing) re-examined at the boundary:
    the structural verifier passed across it with no case it missed (0005 unforced),
    and the one-time router-path gap (business/05) was a *deterministic* alignment
    lever — closed in Milestone 12 Unit 2 (spec 0088) by deferring to compose's
    resolver, not by semantic routing (0006 unforced). The remaining pinned
    divergence (github_actions/05) is an offline-embeddings miss (ADR 0010/0015),
    not a semantic-routing case. This is a documentation pin — if a future measured
    case forces a trigger, this intent is revisited."""
    # The structural verifier produced faithful verdicts across the boundary for
    # every gold case (asserted above); no semantic judge was needed.
    business_answer = ground("business", "What is Müller Logistik's total order value?")
    assert business_answer.all_verified
