"""ER precision/recall, measured (spec 0062).

There is no ER battery in the eval — the three batteries score answer-path
coverage/faithfulness, not merge correctness. Per CLAUDE.md principle 3
("nothing is done until its metric effect is known"), this IS the ER metric: a
labeled pair set (truly-same vs truly-distinct firms/services) scored by each
matcher, so the embedding regime's effect on recall AND precision is a measured
fact, pinned here so drift is loud — **not** a new gated CI floor (faithfulness
stays the only hard one).

The measured table (asserted below):

    matcher           precision   recall
    difflib (0.85)        0.50      0.50    misses checkout-svc/notif-svc; over-merges
    stem-embedding        1.00      1.00    bridges abbreviation + synonym stems
    union  (Unit 4)       0.67      1.00    recall closed; difflib over-merge remains

The honest residual: the union's precision gap is ENTIRELY difflib's pre-existing
generic-suffix over-merge (Granite/Pyrite 0.865, Cobalt/Basalt 0.889). An
*additive* embedding regime cannot remove a difflib false positive — the
stem-embedding regime already shows precision 1.0, so the fix is to apply the same
stem-gating to the difflib pass (a deterministic engine change that would alter
resolve_entities/test_scale — deferred) or multi-field ER (out of scope).

The stub embedder is a keyword-axis toy: it proves a model that places synonym
stems close achieves the measured recall WITHOUT adding false merges. The real
model's recall is the recorded online run (spec 0066), not this test.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import pytest

from tessera.er_semantic import propose_semantic_resolutions
from tessera.platform.vectors import InMemoryVectorStore
from tessera.resolution import DEFAULT_RESOLUTION_THRESHOLD, similarity

Matcher = Callable[[str, str], bool]

# --- the labeled pair set (each negative/positive annotated with its difflib) ---

SHOULD_MERGE = [  # truly the same entity
    ("checkout-service", "checkout-svc"),  # difflib 0.846 — baseline MISS (recall gap)
    (
        "notifications-service",
        "notif-svc",
    ),  # difflib 0.429 — baseline MISS (recall gap)
    ("search-service", "search-servce"),  # difflib 0.960 — baseline HIT (typo)
    ("payments-service", "Payments Service"),  # difflib 1.000 — baseline HIT (case)
]
SHOULD_NOT_MERGE = [  # truly distinct entities
    ("Granite Logistik GmbH", "Pyrite Logistik GmbH"),  # difflib 0.865 — OVER-MERGE
    ("Cobalt Logistik GmbH", "Basalt Logistik GmbH"),  # difflib 0.889 — OVER-MERGE
    ("Müller Logistik GmbH", "Nordwind Logistik GmbH"),  # difflib 0.667 — apart
    ("checkout-service", "payments-service"),  # difflib 0.600 — apart
]


class StubStemEmbeddings:
    """Keyword-axis embedder over stems (no network). A stem fires every axis
    whose keyword is a substring of it, so a synonym stem (``notif`` vs
    ``notifications``) shares an axis while distinct stems stay orthogonal."""

    name = "stub"

    def __init__(self, axes: list[tuple[str, ...]]) -> None:
        self._axes = axes

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [1.0 if any(k in t.lower() for k in axis) else 0.0 for axis in self._axes]
            for t in texts
        ]


# One axis per distinctive concept; "notif" is a substring of "notifications".
_AXES = [
    ("checkout",),
    ("notif",),
    ("search",),
    ("payments",),
    ("granite",),
    ("pyrite",),
    ("cobalt",),
    ("basalt",),
    ("mueller", "muller"),
    ("nordwind",),
]


def _all_names() -> list[str]:
    seen: dict[str, None] = {}  # ordered, de-duplicated
    for a, b in SHOULD_MERGE + SHOULD_NOT_MERGE:
        seen.setdefault(a, None)
        seen.setdefault(b, None)
    return list(seen)


def _precision_recall(
    matcher: Matcher,
) -> tuple[float, float]:
    """Precision/recall of a pair matcher over the labeled set."""
    tp = sum(1 for a, b in SHOULD_MERGE if matcher(a, b))
    fn = len(SHOULD_MERGE) - tp
    fp = sum(1 for a, b in SHOULD_NOT_MERGE if matcher(a, b))
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    return precision, recall


def _difflib_matcher(a: str, b: str) -> bool:
    return similarity(a, b) >= DEFAULT_RESOLUTION_THRESHOLD


def _embedding_merges() -> set[frozenset[str]]:
    """The pairs the stem-embedding regime proposes over the labeled corpus
    (name used as its own node id)."""
    named = [(name, name) for name in _all_names()]
    proposals = propose_semantic_resolutions(
        named, StubStemEmbeddings(_AXES), InMemoryVectorStore()
    )
    return {frozenset({r.node_a, r.node_b}) for r in proposals}


def _embedding_matcher() -> Matcher:
    merges = _embedding_merges()
    return lambda a, b: frozenset({a, b}) in merges


def _union_matcher() -> Matcher:
    embedding = _embedding_matcher()
    return lambda a, b: _difflib_matcher(a, b) or embedding(a, b)


# --- the measured numbers, pinned --------------------------------------------


def test_difflib_baseline_has_a_recall_gap_and_a_precision_gap() -> None:
    precision, recall = _precision_recall(_difflib_matcher)
    # 2/4 positives caught (search-servce, Payments Service); 2 false merges
    # (Granite/Pyrite, Cobalt/Basalt) among predicted merges.
    assert precision == pytest.approx(0.50)
    assert recall == pytest.approx(0.50)


def test_stem_embedding_regime_is_precise_and_higher_recall() -> None:
    precision, recall = _precision_recall(_embedding_matcher())
    # The regime bridges both abbreviation (checkout) and synonym (notif) stems
    # and adds NO false merge — the generic-suffix firms reduce to distinct stems.
    assert precision == pytest.approx(1.00)
    assert recall == pytest.approx(1.00)


def test_union_closes_recall_but_inherits_difflib_overmerge() -> None:
    precision, recall = _precision_recall(_union_matcher())
    # Recall fully closed (the milestone's headline ER win)...
    assert recall == pytest.approx(1.00)
    # ...but precision stays dragged: the embedding adds no FP, yet an additive
    # regime cannot REMOVE difflib's two generic-suffix over-merges (the residual).
    assert precision == pytest.approx(2 / 3)


def test_embedding_adds_exactly_the_two_recall_misses() -> None:
    embedding = _embedding_matcher()
    # The two pairs difflib missed are exactly the ones the embedding regime adds.
    assert embedding("checkout-service", "checkout-svc")
    assert embedding("notifications-service", "notif-svc")
    assert not _difflib_matcher("checkout-service", "checkout-svc")
    assert not _difflib_matcher("notifications-service", "notif-svc")


def test_the_union_precision_gap_is_entirely_difflib() -> None:
    """The residual, asserted: every false merge in the union is a difflib
    over-merge; the embedding regime contributes none."""
    embedding = _embedding_matcher()
    for a, b in SHOULD_NOT_MERGE:
        assert not embedding(a, b), (a, b)  # embedding never over-merges
    difflib_false_merges = {
        frozenset({a, b}) for a, b in SHOULD_NOT_MERGE if _difflib_matcher(a, b)
    }
    assert difflib_false_merges == {
        frozenset({"Granite Logistik GmbH", "Pyrite Logistik GmbH"}),
        frozenset({"Cobalt Logistik GmbH", "Basalt Logistik GmbH"}),
    }
