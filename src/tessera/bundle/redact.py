"""Verifiable redaction — send the receipt without sending the data (spec 0149).

A trust bundle packages the whole evidence closure, which is exactly why it
usually cannot leave the building: customer master data, log lines and
ticket text travel with the decision. Redaction withholds that content
while keeping the artifact verifiable, and — the property that makes it
useful — **without moving the root**: a withheld record contributes the
commitment it was sealed with, so the manifest and root recompute
bit-for-bit identically and a signature or detached approval made over the
original still verifies over the redacted copy (ADR 0039).

The safety property, which the whole design is arranged around:

    Redaction can hide, but it can never upgrade a verdict.

A claim citing withheld evidence is *not* "still verified": it becomes not
re-derivable here, is reported as such, and the bundle can never report a
full PASS again. A redacted bundle proves **less**, never more — which is
also why taking the stored commitment for a withheld leaf is safe.

Pure stdlib and offline, like every trust-path module.
"""

from __future__ import annotations

import copy
from typing import Any

from tessera.bundle.format import is_withheld

#: The marker a withheld section carries.
WITHHELD: dict[str, object] = {"redacted": True}


class RedactionError(ValueError):
    """A named refusal to redact (never a silent, unverifiable artifact)."""


def cited_ids(bundle: dict[str, object]) -> set[str]:
    """Every record id the recorded answer cites."""
    result = bundle.get("result")
    claims = result.get("claims") if isinstance(result, dict) else None
    out: set[str] = set()
    for claim in claims if isinstance(claims, list) else []:
        support = claim.get("support") if isinstance(claim, dict) else None
        for evidence in support if isinstance(support, list) else []:
            identifier = evidence.get("id") if isinstance(evidence, dict) else None
            if isinstance(identifier, str):
                out.add(identifier)
    return out


def keep_closure(bundle: dict[str, object], hops: int = 1) -> set[str]:
    """The cited records plus ``hops`` relation steps.

    One hop is the useful default: the business grammars walk a sales row's
    ``sold_to`` edge to its customer and that customer's resolution cluster,
    so keeping one hop lets aggregate/compare claims still re-derive while
    the rest of the corpus stays home.
    """
    closure = bundle.get("evidence_closure")
    graph = closure.get("graph") if isinstance(closure, dict) else None
    if not isinstance(graph, dict):
        return cited_ids(bundle)

    neighbours: dict[str, set[str]] = {}

    def link(left: object, right: object) -> None:
        if isinstance(left, str) and isinstance(right, str):
            neighbours.setdefault(left, set()).add(right)
            neighbours.setdefault(right, set()).add(left)

    for edge in graph.get("edges") or []:
        if isinstance(edge, dict):
            link(edge.get("src"), edge.get("dst"))
    for resolution in graph.get("resolutions") or []:
        if isinstance(resolution, dict):
            link(resolution.get("node_a"), resolution.get("node_b"))
    for mention in graph.get("mentions") or []:
        if isinstance(mention, dict):
            link(mention.get("node"), mention.get("chunk"))

    keep = set(cited_ids(bundle))
    frontier = set(keep)
    for _ in range(max(0, hops)):
        nxt: set[str] = set()
        for identifier in frontier:
            nxt |= neighbours.get(identifier, set())
        frontier = nxt - keep
        keep |= frontier
    return keep


def redact(
    bundle: dict[str, object],
    keep: set[str] | None = None,
    *,
    hops: int = 1,
    withhold_kb: bool = True,
) -> dict[str, object]:
    """Return a redacted copy: every graph node outside ``keep`` is withheld,
    and (by default) so is the knowledge base, whose records carry the same
    text in bulk.

    The integrity section is carried over untouched — that is what preserves
    the root. Raises :class:`RedactionError` if the bundle is unsealed (there
    would be no commitments to stand in for the withheld content) or if
    redaction would withhold nothing.
    """
    integrity = bundle.get("integrity")
    if not isinstance(integrity, dict) or not isinstance(integrity.get("leaves"), dict):
        raise RedactionError(
            "cannot redact an unsealed bundle: withheld content stands on the "
            "commitments in its integrity manifest"
        )

    working: Any = copy.deepcopy(bundle)
    keep_set = keep_closure(bundle, hops=hops) if keep is None else set(keep)

    closure = working["evidence_closure"]
    graph = closure.get("graph")
    withheld: list[str] = []
    if isinstance(graph, dict):
        nodes = []
        for node in graph.get("nodes") or []:
            identifier = node.get("record", {}).get("id")
            if identifier in keep_set or is_withheld(node):
                nodes.append(node)
                continue
            # The id stays: citations and referential integrity must resolve.
            nodes.append({"redacted": True, "record": {"id": identifier}})
            withheld.append(identifier)
        graph["nodes"] = nodes

    if withhold_kb and not is_withheld(closure.get("kb")):
        closure["kb"] = dict(WITHHELD)
        withheld.append("kb")

    if not withheld:
        raise RedactionError(
            "redaction would withhold nothing — every record is cited or kept"
        )

    # NOTE (corrects spec 0149 D2, kept as a finding): the format minor is NOT
    # bumped. `format` is itself a manifest leaf, so touching it would move the
    # root — and root preservation is the entire point. The per-file
    # feature-level trick works for chains, which are NEW bundles, but not for
    # a transformation of an already-sealed one. A redacted bundle is
    # self-describing through its markers instead of through a version field.
    return working  # type: ignore[no-any-return]


def withheld_ids(bundle: dict[str, object]) -> set[str]:
    """Record ids whose content was withheld (their commitments remain)."""
    closure = bundle.get("evidence_closure")
    graph = closure.get("graph") if isinstance(closure, dict) else None
    if not isinstance(graph, dict):
        return set()
    out: set[str] = set()
    for node in graph.get("nodes") or []:
        if is_withheld(node):
            identifier = node.get("record", {}).get("id")
            if isinstance(identifier, str):
                out.add(identifier)
    return out


def is_redacted(bundle: dict[str, object]) -> bool:
    """Whether any content in this bundle was withheld."""
    closure = bundle.get("evidence_closure")
    if not isinstance(closure, dict):
        return False
    if is_withheld(closure.get("kb")) or is_withheld(closure.get("graph")):
        return True
    return bool(withheld_ids(bundle))
