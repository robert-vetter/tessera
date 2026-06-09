"""Tests for the faithfulness verifier — including the falsifiability proof that
is part of the faithfulness definition (ADR 0005): an injected unfaithful claim
must be caught (is_supported -> False), so a reported 1.0 is earned.
"""

from __future__ import annotations

from tessera.eval.metrics import is_supported
from tessera.graph import Node
from tessera.grounding import Claim, EvidenceRecord
from tessera.knowledge import build_demo_graph


def _nodes() -> dict[str, Node]:
    return {n.id: n for n in build_demo_graph().nodes}


def _record(node_id: str) -> EvidenceRecord:
    return build_demo_graph().node(node_id).record


def test_injected_unfaithful_claim_is_caught() -> None:
    """The adversarial proof: a wrong aggregate over a real row is NOT supported."""
    row = _record("I_SalesDocument:0000500001")  # a real EUR 20,000.00 order
    bogus = Claim("Total net order value across 1 order(s): EUR 999,999.00", (row,))
    assert is_supported(bogus, _nodes()) is False


def test_correct_aggregate_is_supported() -> None:
    row = _record("I_SalesDocument:0000500001")  # EUR 20,000.00
    honest = Claim("Total net order value across 1 order(s): EUR 20,000.00", (row,))
    assert is_supported(honest, _nodes()) is True


def test_snippet_claim_is_supported() -> None:
    row = _record("I_Customer:0010000007")
    claim = Claim(row.text, (row,))  # the claim text is the evidence snippet itself
    assert is_supported(claim, _nodes()) is True


def test_faithfulness_fraction_drops_with_an_injected_unfaithful_claim() -> None:
    """A set containing one unfaithful claim scores below 1.0 — the metric, not
    just the per-claim check, is provably able to fail."""
    nodes = _nodes()
    row = _record("I_SalesDocument:0000500001")
    honest = Claim("Total net order value across 1 order(s): EUR 20,000.00", (row,))
    bogus = Claim("Total net order value across 1 order(s): EUR 999,999.00", (row,))
    claims = [honest, bogus]
    supported = sum(1 for c in claims if is_supported(c, nodes))
    assert supported / len(claims) < 1.0


def test_count_claim_unsupported_when_cited_records_do_not_match() -> None:
    """A claim asserting an address record it does not cite is unfaithful."""
    customer = _record("I_Customer:0010000007")
    claim = Claim(
        "'X' is one resolved entity spanning 1 customer record(s) and 1 address "
        "record(s).",
        (
            customer,
        ),  # cites the customer but NOT an address — so '1 address' is unbacked
    )
    assert is_supported(claim, _nodes()) is False
