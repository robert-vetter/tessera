"""The fidelity bridge: model semantics vs. the shipping verifier (spec 0147).

A proof about a model is worth exactly as much as the model's agreement
with the code. So the model's claim semantics are not asserted to match
the implementation — they are **checked against it**, exhaustively, over
the same bounded domain: every model claim is materialised into real
:class:`~tessera.grounding.EvidenceRecord` / :class:`~tessera.graph.Node` /
:class:`~tessera.grounding.Claim` objects and evaluated by the real
:func:`~tessera.eval.metrics.is_supported` with the real
:data:`~tessera.business.claims.BUSINESS_CLAIM_SHAPES`.

Scope of the bridge, stated precisely:

- It covers claims whose citations are all **packaged**. A claim citing a
  record that is not in the graph is refused earlier, by the verifier's
  referential-integrity check (spec 0134), not by ``is_supported``; the
  model mirrors that refusal and the existing verifier tests pin it.
- ``SUM`` maps to the real aggregate-recomputation grammar, ``QUOTE`` to
  the real verbatim-containment grammar — including its ``any(...)``
  semantics over cited records, which the model copies rather than
  idealises.
"""

from __future__ import annotations

from dataclasses import dataclass

from tessera.business.claims import BUSINESS_CLAIM_SHAPES
from tessera.eval.metrics import is_supported
from tessera.graph import Node
from tessera.grounding import Claim as RealClaim
from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.proof.model import Claim, Kind

_SOURCE = "salt_synthetic/I_SalesDocument.csv"
_INGESTED_AT = "2026-01-01"


def record_text(value: int) -> str:
    """The evidence text a model record materialises to. Deliberately free
    of the phrase the aggregate grammar keys on, so a QUOTE claim exercises
    containment and nothing else."""
    return f"Sales order line, net EUR {value:,.2f}."


def claim_text(claim: Claim) -> str:
    if claim.kind is Kind.SUM:
        return (
            f"'Acme GmbH': total net order value across {len(claim.cited)} "
            f"order(s): EUR {claim.asserted:,.2f}."
        )
    return record_text(claim.asserted)


def _node(index: int, value: int) -> Node:
    record = EvidenceRecord(
        id=f"r{index}",
        origin=Origin(
            source=_SOURCE,
            locator=Locator(kind="table-row", parts=(("row", str(index)),)),
            ingested_at=_INGESTED_AT,
        ),
        text=record_text(value),
    )
    return Node(
        record=record,
        kind="I_SalesDocument",
        attributes=(("net_amount", f"{value}.00"), ("currency", "EUR")),
    )


def real_verdict(claim: Claim, records: tuple[int, ...]) -> bool:
    """Evaluate a model claim with the **shipping** verifier core."""
    nodes = {f"r{i}": _node(i, value) for i, value in enumerate(records)}
    support = tuple(nodes[f"r{i}"].record for i in claim.cited)
    real = RealClaim(text=claim_text(claim), support=support)
    return is_supported(real, nodes, None, BUSINESS_CLAIM_SHAPES)


@dataclass(frozen=True)
class Disagreement:
    """A model claim whose semantics diverge from the implementation — a
    finding to record and fix, never to work around."""

    records: tuple[int, ...]
    kind: str
    cited: tuple[int, ...]
    asserted: int
    model: bool
    implementation: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "records": list(self.records),
            "kind": self.kind,
            "cited": list(self.cited),
            "asserted": self.asserted,
            "model_says": self.model,
            "implementation_says": self.implementation,
        }


def check_fidelity(
    corpora: list[tuple[int, ...]], claims: list[Claim]
) -> tuple[int, tuple[Disagreement, ...]]:
    """Compare model and implementation on every (corpus, claim) pair whose
    citations are packaged. Returns (checked, disagreements)."""
    checked = 0
    problems: list[Disagreement] = []
    for records in corpora:
        for claim in claims:
            if any(index >= len(records) for index in claim.cited):
                continue  # referential integrity: the verifier's path, not this one
            model = claim.is_valid(records)
            implementation = real_verdict(claim, records)
            checked += 1
            if model != implementation:
                problems.append(
                    Disagreement(
                        records=records,
                        kind=claim.kind.value,
                        cited=claim.cited,
                        asserted=claim.asserted,
                        model=model,
                        implementation=implementation,
                    )
                )
    return checked, tuple(problems)
