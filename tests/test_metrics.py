"""Tests for the faithfulness verifier — including the falsifiability proof that
is part of the faithfulness definition (ADR 0005): an injected unfaithful claim
must be caught (is_supported -> False), so a reported 1.0 is earned.
"""

from __future__ import annotations

from tessera.business.claims import BUSINESS_CLAIM_SHAPES
from tessera.business.knowledge import build_demo_graph
from tessera.eval.metrics import is_supported
from tessera.graph import Node
from tessera.grounding import Claim, EvidenceRecord


def _nodes() -> dict[str, Node]:
    return {n.id: n for n in build_demo_graph().nodes}


def _record(node_id: str) -> EvidenceRecord:
    return build_demo_graph().node(node_id).record


def test_injected_unfaithful_claim_is_caught() -> None:
    """The adversarial proof: a wrong aggregate over a real row is NOT supported."""
    row = _record("I_SalesDocument:0000500001")  # a real EUR 20,000.00 order
    bogus = Claim("Total net order value across 1 order(s): EUR 999,999.00", (row,))
    assert is_supported(bogus, _nodes(), shapes=BUSINESS_CLAIM_SHAPES) is False


def test_correct_aggregate_is_supported() -> None:
    row = _record("I_SalesDocument:0000500001")  # EUR 20,000.00
    honest = Claim("Total net order value across 1 order(s): EUR 20,000.00", (row,))
    assert is_supported(honest, _nodes(), shapes=BUSINESS_CLAIM_SHAPES) is True


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
    supported = sum(
        1 for c in claims if is_supported(c, nodes, shapes=BUSINESS_CLAIM_SHAPES)
    )
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
    assert is_supported(claim, _nodes(), shapes=BUSINESS_CLAIM_SHAPES) is False


def test_verifier_core_contains_no_vertical_vocabulary() -> None:
    """The ADR 0011 guard: eval/metrics.py must stay vertical-neutral. If a
    vertical's grammar leaks back in, this fails loudly."""
    from pathlib import Path

    import tessera.eval.metrics as metrics_module

    source = Path(metrics_module.__file__).read_text("utf-8")
    for leaked in (
        "net order value",
        "I_Customer",
        "renewal",
        "Refused to sum",
        "order(s)",
        "tessera.business.conflicts",
    ):
        assert leaked not in source, leaked
