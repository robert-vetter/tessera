"""The faithfulness verifier core — deterministic, vertical-neutral, able to fail.

``is_supported`` decides whether one claim's content is actually backed by its
cited evidence. The core knows only the grammars that are genuinely
vertical-neutral (ADR 0008/0011): the **shared-fragment** shape (a quoted
fragment asserted to occur in several named sources) and **verbatim
containment** (the claim text appears in a cited record). Every other grammar
belongs to the vertical that composes it, expressed as a :data:`ClaimShape`
and carried to the harness by its battery
(:mod:`tessera.eval.registry` → :mod:`tessera.eval.battery`) — e.g. the
business grammars in :mod:`tessera.business.claims`.

It is the core of the faithfulness metric (ADR 0005): a claim that asserts
anything its citations do not support returns ``False``, so faithfulness can
— and is tested to — drop below 1.0. No LLM; pure deterministic checks.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence

from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import Claim
from tessera.resolution import normalize

# A vertical-owned claim grammar (ADR 0011). Returns an OWNED verdict (bool)
# when the claim speaks its grammar, or None when it does not — in which case
# the next shape, and finally the generic grammars below, are consulted.
ClaimShape = Callable[
    [Claim, Mapping[str, Node], "KnowledgeGraph | None"], "bool | None"
]

# Shared-fragment claims: '… "FRAGMENT" appears in 'SRC_A' and 'SRC_B'.'
# Vertical-neutral by construction (ADR 0008): the claim asserts only that a
# quoted evidence fragment occurs in the named sources — a recurring log
# signature, a ticket id shared by a PR and a tracker row, a clause echoed
# across documents are all the same shape. Sources are parsed from the tail
# only, so single quotes INSIDE the fragment cannot masquerade as sources;
# a fragment containing a double quote does not parse and the claim simply
# fails verification (honest, not lenient).
_SHARED_FRAGMENT = re.compile(r'"([^"]+)" appears in ([^"]+)$')
_NAMED_SOURCES = re.compile(r"'([^']+)'")


def is_supported(
    claim: Claim,
    nodes: Mapping[str, Node],
    graph: KnowledgeGraph | None = None,
    shapes: Sequence[ClaimShape] = (),
) -> bool:
    """True iff the claim's content is deterministically backed by its citations.

    ``nodes`` maps a record id to its graph node so shapes can re-check claims
    against the structured attributes of exactly the cited rows; ``graph``
    (optional) enables shapes that recompute conclusions over entities.
    ``shapes`` are the owning battery's declared grammars, consulted first and
    in order (ADR 0011); the generic grammars follow; anything unclaimed is
    unsupported.
    """
    text = claim.text

    # 1) The vertical's own grammars, in the battery's declared order.
    for shape in shapes:
        verdict = shape(claim, nodes, graph)
        if verdict is not None:
            return verdict

    # 2) Shared fragment: the quoted fragment must appear in EVERY cited
    #    record, and the named sources must be exactly the cited origins.
    #    This grammar owns its verdict — no fallthrough to containment.
    shared = _SHARED_FRAGMENT.search(text)
    if shared:
        fragment = shared.group(1)
        named = set(_NAMED_SOURCES.findall(shared.group(2)))
        if len(claim.support) < 2 or len(named) < 2:
            return False
        if named != {rec.origin.source for rec in claim.support}:
            return False
        needle_fragment = normalize(fragment)
        return bool(needle_fragment) and all(
            needle_fragment in normalize(rec.text) for rec in claim.support
        )

    # 3) Surfaced snippet / document clause: the claim text appears verbatim
    #    (normalized) in a cited record. Anything unclaimed is unsupported.
    needle = normalize(text)
    return bool(needle) and any(needle in normalize(rec.text) for rec in claim.support)
