"""Standing-trigger specimens: where the deterministic approach reaches its edge.

Each of the three live revisit triggers — LLM-judged faithfulness (ADR 0005),
embeddings (ADR 0010), semantic routing (ADR 0006) — is demonstrated here as a
concrete, committed fact, so its firing condition is precise rather than abstract.
NONE is acted on this milestone: the maintainer chose to hold the determinism
line (spec 0043), so crossing into an LLM/embedding dependency is escalated, not
done. These specimens are the evidence that the limits are real AND that no
*measured* case yet forces crossing the line.
"""

from __future__ import annotations

from itertools import combinations

from tessera.business.reasoning import mentions_superlative
from tessera.eval.metrics import is_supported
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import Claim, EvidenceRecord, Locator, Origin
from tessera.resolution import normalize, similarity
from tessera.sources.github_actions import GitHubActionsSource


def _doc(rid: str, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=rid,
        origin=Origin(
            source=f"specimen/{rid}.log",
            locator=Locator(kind="log-span", parts=(("chunk", "1"),)),
            ingested_at="2026-06-16",
        ),
        text=text,
    )


def test_adr0005_verbatim_but_misleading_claim_passes_structural_faithfulness() -> None:
    """ADR 0005 blind spot, demonstrated. The verifier checks a fragment is
    verbatim-contained in every cited record — not that the shared fragment is a
    MEANINGFUL link. Two unrelated failures that merely share a generic trailer
    yield a 'recurring failure' claim that is structurally faithful yet
    misleading; only a semantic (LLM) judge could catch it. The standing trigger
    to add one has not fired on a measured case precisely because the engine is
    built to key on the most specific line, not the generic trailer (spec 0046)."""
    graph = KnowledgeGraph()
    a = _doc("A", "Build of service-a failed.\nProcess completed with exit code 1.")
    b = _doc("B", "Linting of service-b failed.\nProcess completed with exit code 1.")
    graph.add_node(Node(record=a, kind="document"))
    graph.add_node(Node(record=b, kind="document"))
    nodes = {n.id: n for n in graph.nodes}

    misleading = Claim(
        text=(
            'Recurring failure: "Process completed with exit code 1" '
            "appears in 'specimen/A.log' and 'specimen/B.log'."
        ),
        support=(a, b),
    )
    # Structurally faithful — the fragment IS verbatim in both records …
    assert is_supported(misleading, nodes, graph)
    # … yet the two failures are unrelated (a build vs a lint); the shared line is
    # a generic trailer, not a common cause. Structure cannot tell the difference.

    # The verifier is not broken — a fragment NOT in both is still rejected.
    tampered = Claim(
        text=(
            'Recurring failure: "TimeoutError in payments" '
            "appears in 'specimen/A.log' and 'specimen/B.log'."
        ),
        support=(a, b),
    )
    assert not is_supported(tampered, nodes, graph)


def test_adr0010_error_class_synonymy_is_undeclarable() -> None:
    """ADR 0010 refreshed trigger, demonstrated. A declared catalog alias closes
    a NAME variance (notif-svc ↔ notifications-service — the same service,
    abbreviated). The real Pages-deploy failure has a different shape: three
    surface forms of ONE root cause that share no bridgeable string. No catalog
    field could declare '404 means Pages-not-enabled'; only semantics could link
    them. That is the precise embeddings case — a measured miss no declarable
    data could fix."""
    # The DECLARABLE case (closed in Phase 4): the abbreviation and the canonical
    # are the same name; a declared alias asserts their identity.
    assert "notif" in normalize("notif-svc")
    assert "notif" in normalize("notifications-service")

    # The UNDECLARABLE case: three real surface forms of the Pages-deploy failure,
    # all present in the committed real log, mutually un-bridgeable by any string.
    forms = (
        "HttpError: Not Found",
        "status: 404",
        "Ensure GitHub Pages has been enabled",
    )
    for x, y in combinations(forms, 2):
        assert similarity(x, y) < 0.35  # no string bridge a declared alias could use

    real_log = "\n".join(
        r.text
        for r in GitHubActionsSource().ingest()
        if r.origin.locator.kind == "log-span"
    )
    for form in forms:
        assert form in real_log  # the synonymy is real and present, not invented


def test_adr0006_intent_verbs_remain_the_router_ceiling() -> None:
    """ADR 0006, named. Words that carry the ranking intent only semantically
    ('rank', 'order', 'lead', 'best') are deliberately not pattern-matched — the
    documented router ceiling (spec 0048). Upgrading the router to understand
    them needs the LLM ADR 0006 holds in reserve; no gold/synthetic case yet
    forces it (a correct refusal is the honest fallback)."""
    for phrasing in ("rank our clients", "order them by revenue", "our best account"):
        assert not mentions_superlative(phrasing)
