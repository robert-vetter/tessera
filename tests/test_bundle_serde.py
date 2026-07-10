"""Fidelity tests for the bundle reconstruction layer (spec 0132).

Three properties are pinned: losslessness (``to_dict → from_dict → to_dict``
byte-identical under canonical dumps; graphs tuple-exact), strictness
(malformed input raises ``ValueError`` naming the key), and — the point of
the whole unit — the re-verification bridge: claims and a graph rebuilt from
dicts alone re-derive exactly the recorded boundary verdicts through the
eval's own ``is_supported``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera.agent.actions import draft_action
from tessera.agent.execution import execute_action
from tessera.agent.grounded import domain, ground, verify_claims
from tessera.agent.payloads import preview_payload
from tessera.bundle import serde
from tessera.eval.metrics import is_supported
from tessera.grounding import Answer

_DOMAINS = ("business", "devex", "github_actions")

# A representative grounded question per domain (the deterministic router
# grounds these; same set the agent-layer tests use) and one that refuses.
_GROUNDED = {
    "business": "Compare Müller Logistik and Nordwind Logistik totals.",
    "devex": "Why did run R-1042 fail, and has this happened before?",
    "github_actions": "Why did the pages deploy fail?",
}
_REFUSED = "What is the meaning of life?"


def _canonical(data: dict[str, object]) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# --- graph and knowledge base ---------------------------------------------------


@pytest.mark.parametrize("name", _DOMAINS)
def test_graph_round_trip_is_tuple_exact_and_byte_identical(name: str) -> None:
    graph, _ = domain(name).build()
    snapshot = serde.graph_to_dict(graph)
    rebuilt = serde.graph_from_dict(snapshot)
    assert rebuilt.nodes == graph.nodes
    assert rebuilt.edges == graph.edges
    assert rebuilt.resolutions == graph.resolutions
    assert rebuilt.mentions == graph.mentions
    assert _canonical(serde.graph_to_dict(rebuilt)) == _canonical(snapshot)


@pytest.mark.parametrize("name", _DOMAINS)
def test_kb_round_trip_is_byte_identical(name: str) -> None:
    _, kb = domain(name).build()
    snapshot = serde.kb_to_dict(kb)
    rebuilt = serde.kb_from_dict(snapshot)
    assert serde.kb_from_dict(serde.kb_to_dict(rebuilt)) == rebuilt
    assert _canonical(serde.kb_to_dict(rebuilt)) == _canonical(snapshot)


def test_graph_rebuild_derives_identical_clusters() -> None:
    """Derived state (resolved-entity clusters) is a function of the replayed
    assertions, so a rebuilt graph derives the same entities."""
    graph, _ = domain("business").build()
    rebuilt = serde.graph_from_dict(serde.graph_to_dict(graph))
    assert sorted(map(sorted, rebuilt.clusters())) == sorted(
        map(sorted, graph.clusters())
    )


# --- the grounded answer ---------------------------------------------------------


@pytest.mark.parametrize("name", _DOMAINS)
def test_grounded_result_round_trip_grounded(name: str) -> None:
    result = ground(name, _GROUNDED[name])
    assert result.grounded and result.claims
    data = result.to_dict()
    rebuilt = serde.grounded_result_from_dict(data)
    assert rebuilt == result
    assert _canonical(rebuilt.to_dict()) == _canonical(data)


@pytest.mark.parametrize("name", _DOMAINS)
def test_grounded_result_round_trip_refusal(name: str) -> None:
    result = ground(name, _REFUSED)
    assert result.refused and result.refusal
    data = result.to_dict()
    rebuilt = serde.grounded_result_from_dict(data)
    assert rebuilt == result
    assert _canonical(rebuilt.to_dict()) == _canonical(data)


# --- the action chain -------------------------------------------------------------


def test_action_proposal_round_trip_grounded_and_refused() -> None:
    grounded = draft_action("incident", "devex", _GROUNDED["devex"])
    assert grounded.all_grounded
    refused = draft_action("incident", "business", _GROUNDED["business"])
    assert refused.refused
    for proposal in (grounded, refused):
        data = proposal.to_dict()
        rebuilt = serde.action_proposal_from_dict(data)
        assert rebuilt == proposal
        assert _canonical(rebuilt.to_dict()) == _canonical(data)


def test_rendered_payload_round_trip_rendered_and_withheld() -> None:
    rendered = preview_payload("incident", "devex", _GROUNDED["devex"])
    assert rendered.rendered
    withheld = preview_payload("incident", "business", _GROUNDED["business"])
    assert not withheld.rendered and withheld.withheld_reason
    for payload in (rendered, withheld):
        data = payload.to_dict()
        rebuilt = serde.rendered_payload_from_dict(data)
        assert rebuilt == payload
        assert _canonical(rebuilt.to_dict()) == _canonical(data)


def test_execution_receipt_round_trip_simulated_live() -> None:
    receipt = execute_action("incident", "devex", _GROUNDED["devex"])
    assert receipt.simulated and receipt.executed and not receipt.sent
    data = receipt.to_dict()
    rebuilt = serde.execution_receipt_from_dict(data)
    assert rebuilt == receipt
    assert _canonical(rebuilt.to_dict()) == _canonical(data)


def test_execution_receipt_round_trip_committed_fixture() -> None:
    """The one real, scrubbed receipt on the record (Milestone 15) reconstructs
    and re-serializes byte-identically under canonical dumps."""
    raw = json.loads(
        (Path("data") / "execution" / "receipt.json").read_text(encoding="utf-8")
    )
    rebuilt = serde.execution_receipt_from_dict(raw)
    assert _canonical(rebuilt.to_dict()) == _canonical(raw)


# --- the re-verification bridge ----------------------------------------------------


def test_rebuilt_claims_and_graph_rederive_recorded_verdicts() -> None:
    """The unit's reason to exist: from serialized dicts ALONE — the grounded
    result and the graph snapshot — rebuild the verifier's inputs and re-run
    ``is_supported``; the re-derived verdicts must equal the recorded
    boundary verdicts. (The full equality floor over all gold cases is
    unit 0134.)"""
    graph, _ = domain("business").build()
    result = ground("business", _GROUNDED["business"])
    assert result.grounded and result.claims

    # Cross the serialization boundary in both directions.
    rebuilt_graph = serde.graph_from_dict(
        json.loads(json.dumps(serde.graph_to_dict(graph)))
    )
    rebuilt_result = serde.grounded_result_from_dict(
        json.loads(json.dumps(result.to_dict()))
    )

    nodes = {node.id: node for node in rebuilt_graph.nodes}
    shapes = domain("business").claim_shapes
    rederived = tuple(
        is_supported(serde.claim_from_grounded(claim), nodes, rebuilt_graph, shapes)
        for claim in rebuilt_result.claims
    )
    assert rederived == tuple(claim.verified for claim in rebuilt_result.claims)
    assert all(rederived)


def test_verify_claims_agrees_across_the_boundary() -> None:
    """The same re-derivation through the boundary's own ``verify_claims``
    entry point, over a rebuilt Answer — the exact call path unit 0134's
    verifier will use."""
    graph, _ = domain("devex").build()
    result = ground("devex", _GROUNDED["devex"])
    rebuilt_graph = serde.graph_from_dict(serde.graph_to_dict(graph))
    rebuilt_result = serde.grounded_result_from_dict(result.to_dict())
    answer = Answer(
        question=rebuilt_result.question,
        claims=tuple(
            serde.claim_from_grounded(claim) for claim in rebuilt_result.claims
        ),
        refusal=None,
    )
    verdicts = verify_claims(answer, rebuilt_graph, domain("devex").claim_shapes)
    assert verdicts == tuple(claim.verified for claim in rebuilt_result.claims)


# --- strictness ---------------------------------------------------------------------


def test_missing_key_raises_valueerror_naming_it() -> None:
    with pytest.raises(ValueError, match="'text'"):
        serde.claim_from_dict({"support": []})


def test_wrong_type_raises_valueerror_naming_it() -> None:
    with pytest.raises(ValueError, match="'kind'"):
        serde.locator_from_dict({"kind": 7, "parts": []})


def test_malformed_pair_raises_valueerror_with_index() -> None:
    with pytest.raises(ValueError, match=r"parts\[0\]"):
        serde.locator_from_dict({"kind": "table-row", "parts": [["only-one"]]})


def test_derived_fields_are_recomputed_not_read_back() -> None:
    """``all_verified`` is a property of the rebuilt object; a tampered stored
    value cannot survive reconstruction."""
    result = ground("business", _GROUNDED["business"])
    data = result.to_dict()
    data["all_verified"] = False  # lie in the stored derived field
    rebuilt = serde.grounded_result_from_dict(data)
    assert rebuilt.all_verified  # recomputed from the claims, not read back
