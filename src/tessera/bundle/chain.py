"""Chained trust bundles — a verified bundle becomes evidence (spec 0143).

The audit trail for agent pipelines: a chain bundle's evidence corpus is
derived **exclusively from other bundles' verifier-passing claims**, and the
upstream bundles travel embedded in the chain's evidence closure (ADR 0033),
so one file still verifies offline, alone. Emission enforces "cite only what
re-verifies": every upstream is fully re-verified here first, and a non-PASS
upstream refuses to chain with a named reason. Verification (unit 0134's
chain branch) re-checks all of it — the emitter is never trusted either.

The chain *answer* is deliberately modest: the frozen core's deterministic
lexical retrieval over the derived claim records (called, never modified),
with its principled refusal. A chain bundle cites upstream findings; it
computes nothing new — cross-bundle aggregation is named future work, not
smuggled in.

Pure stdlib and offline, like every trust-path module.
"""

from __future__ import annotations

from collections.abc import Mapping

from tessera.agent.grounded import serialize_answer
from tessera.bundle.emit import engine_version, shape_identifiers
from tessera.bundle.format import (
    CHAIN_DOMAIN,
    CHAIN_FORMAT_MINOR,
    CLOSURE_CHAIN,
    FORMAT_MAJOR,
    FORMAT_NAME,
    seal,
)
from tessera.bundle.serde import graph_to_dict, kb_to_dict
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import (
    Answer,
    Claim,
    EvidenceRecord,
    KnowledgeBase,
    Locator,
    Origin,
)
from tessera.retrieval import answer as retrieve_answer
from tessera.routing import Route

#: Locator kind for a record derived from an upstream bundle's claim. A new
#: kind on the unchanged kind-tagged Locator (ADR 0002, cashed again).
BUNDLE_CLAIM = "bundle-claim"

#: ``Origin.ingested_at`` for chain records. Bundles carry no wall-clock by
#: design (byte-stable emission, ADR 0031); the honest snapshot identity of a
#: derived record is "the upstream's sealed state", named as such.
INGESTED_AT = "at-upstream-seal"


class ChainError(ValueError):
    """A named refusal to build a chain bundle (never a silent downgrade)."""


def chain_citation(
    claim: Claim, nodes: Mapping[str, Node], graph: KnowledgeGraph | None
) -> bool | None:
    """The chain claim grammar (spec 0143 D4): a claim is a **verbatim
    citation** of exactly one derived bundle-claim record in the packaged
    corpus. It owns the verdict for such claims — the generic grammars (e.g.
    the shared-fragment recomputation) must not re-argue an upstream claim
    against the *chain* corpus, where the upstream's raw sources rightly do
    not exist. The deeper truth of the cited statement is re-established by
    the recursive upstream re-verification (verify's chain layer), not here.
    """
    if len(claim.support) != 1:
        return None
    record = claim.support[0]
    if record.origin.locator.kind != BUNDLE_CLAIM:
        return None
    node = nodes.get(record.id)
    if node is None:
        return False  # cites a record that is not in the packaged corpus
    corpus_record = node.record
    if corpus_record.origin.locator.kind != BUNDLE_CLAIM:
        return False
    return claim.text == corpus_record.text


#: The chain domain's declared grammars, carried in ``engine.claim_shapes``
#: like any vertical's (ADR 0011) and re-checked identically at verify.
CHAIN_CLAIM_SHAPES = (chain_citation,)


def _short(root: str) -> str:
    """A readable root prefix for messages: ``sha256:`` plus 12 hex chars."""
    return root[:19] + "…" if len(root) > 20 else root


def bundle_root(bundle: dict[str, object]) -> str:
    """The sealed root of a bundle dict, or a :class:`ChainError` naming why
    it cannot be read (an unsealed dict has no identity to chain on)."""
    integrity = bundle.get("integrity")
    root = integrity.get("root") if isinstance(integrity, dict) else None
    if not isinstance(root, str) or not root:
        raise ChainError("an upstream bundle carries no sealed integrity root")
    return root


def _claim_records(
    upstream: dict[str, object], root: str, rederived: tuple[bool, ...]
) -> list[EvidenceRecord]:
    """The derived evidence records for one verified upstream: one record per
    claim that is recorded verified AND re-derived here, text byte-for-byte."""
    result = upstream.get("result")
    claims = result.get("claims") if isinstance(result, dict) else None
    if not isinstance(claims, list):
        return []
    records: list[EvidenceRecord] = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            continue
        text = claim.get("text")
        if not isinstance(text, str):
            continue
        if claim.get("verified") is not True:
            continue
        if index >= len(rederived) or not rederived[index]:
            continue
        records.append(
            EvidenceRecord(
                id=f"chain:{root.removeprefix('sha256:')[:12]}:c{index}",
                origin=Origin(
                    source=f"bundle:{root}",
                    locator=Locator(
                        kind=BUNDLE_CLAIM,
                        parts=(("bundle", root), ("claim", str(index))),
                    ),
                    ingested_at=INGESTED_AT,
                ),
                text=text,
            )
        )
    return records


def chain_corpus(
    upstreams: list[dict[str, object]],
) -> tuple[KnowledgeGraph, KnowledgeBase]:
    """Verify every upstream and derive the chain corpus from their
    verifier-passing claims. Raises :class:`ChainError`, named, when an
    upstream does not PASS, when two upstreams share a root, or when nothing
    is citable (a chain with no evidence would be an empty attestation)."""
    from tessera.bundle.verify import BundleFormatError, verify_bundle

    if not upstreams:
        raise ChainError("a chain needs at least one upstream bundle")

    seen: set[str] = set()
    records: list[EvidenceRecord] = []
    for position, upstream in enumerate(upstreams):
        root = bundle_root(upstream)
        if root in seen:
            raise ChainError(f"upstream {_short(root)} is embedded twice")
        seen.add(root)
        try:
            report = verify_bundle(upstream)
        except BundleFormatError as error:
            raise ChainError(
                f"upstream {position} ({_short(root)}) cannot be verified: {error}"
            ) from error
        if report.verdict != "PASS":
            cause = (
                report.taxonomy_reason
                or "; ".join(report.semantic_problems[:1])
                or "; ".join(report.envelope_problems[:1])
                or report.verdict
            )
            raise ChainError(
                f"cite only what re-verifies: upstream {_short(root)} is "
                f"{report.verdict} ({cause})"
            )
        records.extend(
            _claim_records(upstream, root, tuple(c.rederived for c in report.claims))
        )

    if not records:
        raise ChainError(
            "nothing citable: the upstream bundle(s) carry no verifier-passing "
            "claims (a refusal has no claims to cite)"
        )

    graph = KnowledgeGraph()
    for record in records:
        graph.add_node(Node(record=record, kind=BUNDLE_CLAIM))
    return graph, KnowledgeBase(records=tuple(records))


def chain_route(
    question: str, graph: KnowledgeGraph, kb: KnowledgeBase
) -> tuple[Route, Answer]:
    """The deterministic chain router: the frozen core's lexical retrieval
    (BM25 + principled refusal) over the derived claim records. Its reason is
    computed from the corpus content only, so verification re-derives it."""
    sources = {record.origin.source for record in kb.records}
    route = Route(
        kind="chain",
        reason=(
            f"cites the verifier-passing claims of {len(sources)} upstream "
            "trust bundle(s)"
        ),
    )
    return route, retrieve_answer(question, kb)


def build_chain_bundle(
    upstreams: list[dict[str, object]], question: str
) -> dict[str, object]:
    """Build and seal a chain bundle over already-parsed upstream bundle
    dicts. Raises :class:`ChainError` (named) rather than ever chaining an
    upstream that does not re-verify."""
    graph, kb = chain_corpus(upstreams)
    route, answer = chain_route(question, graph, kb)
    result = serialize_answer(
        answer,
        graph,
        CHAIN_CLAIM_SHAPES,
        domain=CHAIN_DOMAIN,
        question=question,
        route=route,
    )
    unsealed: dict[str, object] = {
        "format": {
            "name": FORMAT_NAME,
            "major": FORMAT_MAJOR,
            "minor": CHAIN_FORMAT_MINOR,
        },
        "engine": {
            "tessera_version": engine_version(),
            "domain": CHAIN_DOMAIN,
            "claim_shapes": shape_identifiers(CHAIN_CLAIM_SHAPES),
        },
        "result": result.to_dict(),
        "evidence_closure": {
            "kind": CLOSURE_CHAIN,
            "graph": graph_to_dict(graph),
            "kb": kb_to_dict(kb),
            "upstream": list(upstreams),
        },
        "action": None,
        "signature": None,
        "anchor": None,
    }
    return seal(unsealed)
