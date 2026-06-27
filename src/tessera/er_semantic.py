"""Embedding-assisted entity resolution (ADR 0016).

A **second, additive** resolution regime alongside the deterministic ``difflib``
pass (:mod:`tessera.resolution` and ``KnowledgeGraph.resolve_entities``). It
proposes same-entity :class:`~tessera.graph.Resolution`\\s from a **semantic**
name signal, so abbreviation/synonym variants that *character* similarity misses
can still merge — without lowering the global 0.85 threshold (which would
catastrophically over-merge generic-suffix firms; ADR 0010/0015).

The hard problem is that the two failure modes pull in **opposite directions**:

- ``checkout-service ↔ checkout-svc`` (``difflib`` 0.846, just under the
  threshold) is a **recall** miss — it needs *more* merging.
- ``Granite/Pyrite/Cobalt/Basalt Logistik GmbH`` (measured in
  ``tests/test_scale.py``) is a **precision** error — it needs *less* merging.

A naive name-cosine pass fixes the first and worsens the second (the full names
are semantically near-identical: same industry token + legal form). The fix is to
embed the **distinctive stem** — the name with its *generic* tokens removed — and
merge on the stem cosine. One rule resolves the tension:

- ``checkout-service`` and ``checkout-svc`` both reduce to the stem ``checkout``
  (``service``/``svc`` are generic), so they merge;
- ``Granite Logistik GmbH`` and ``Pyrite Logistik GmbH`` reduce to ``granite`` /
  ``pyrite`` (``logistik``/``gmbh`` are generic), which stay apart;
- ``notif-svc`` and ``notifications-service`` reduce to ``notif`` / ``notifications``,
  which a real model places close — a **declaration-free** synonym bridge that no
  catalog alias was needed for (the genuine embedding win).

**Where each gain comes from, honestly.** Stem extraction is deterministic: it
alone closes ``checkout-svc`` (the stems become string-identical) and alone
prevents the generic-suffix over-merge. The *model* earns the cases where the
distinctive stems are synonyms but **not** string-identical
(``notif ↔ notifications``) — that is the part that needs the online run, and the
part this regime adds over a pure stoplist.

**Embeddings serve linking only** — the ADR 0015 line, now applied to ER. The
faithfulness verifier (`eval/metrics.py`) imports nothing from here (the
leak-guard banned set includes this module); ER decisions are written back as
ordinary additive, reversible ``graph.Resolution``\\s; this module never mutates a
node and never touches the claim path. It imports the graph/resolution/platform
modules one-directionally — they never import it.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from typing import Protocol

from tessera.graph import Resolution
from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.platform.providers import EmbeddingProvider
from tessera.platform.vectors import InMemoryVectorStore, VectorStore
from tessera.resolution import LEGAL_SUFFIXES, normalize


class _IndexableRetriever(Protocol):
    """A record-shaped semantic index that can be filled and queried — the half
    of the backends (``HanaSemanticIndex`` / ``SemanticIndex``) the via-index
    proposer needs. (``SemanticRetriever`` itself only exposes ``retrieve``.)"""

    def index(self, records: tuple[EvidenceRecord, ...]) -> None: ...

    def retrieve(
        self, question: str, k: int = ...
    ) -> list[tuple[EvidenceRecord, float]]: ...


# The cosine at/above which two distinctive stems are asserted to co-refer. Named,
# documented, and tunable on purpose (the analogue of
# ``DEFAULT_RESOLUTION_THRESHOLD``): the Unit 3 ER precision/recall measurement is
# its revisit trigger. It is a **cosine** threshold (a different metric than the
# ``difflib`` ratio), applied to the stems, not the full names.
DEFAULT_SEMANTIC_THRESHOLD = 0.85

# A token shared across at least this many names is treated as generic (a
# corpus-frequency stoplist, so "Logistik" across four firms becomes generic
# without anyone naming it). Tunable; small by design so single-occurrence
# distinctive stems are never stripped.
DEFAULT_MIN_GENERIC_DF = 3

# Universal organizational descriptors — generic regardless of corpus frequency,
# because they describe *kind*, not *identity* (unlike a per-entity alias, ADR
# 0010). Kept small and explicit; legal forms are folded in from
# :data:`tessera.resolution.LEGAL_SUFFIXES`.
ORG_DESCRIPTORS = frozenset(
    {"service", "services", "svc", "svcs", "system", "systems", "platform", "app"}
)

_TOKEN_SPLIT = re.compile(r"[\s\-_/.,&]+")


def tokenize(name: str) -> list[str]:
    """Split a name into normalized tokens (lowercased, umlaut/diacritic-folded).

    Each token is run through :func:`tessera.resolution.normalize` so
    ``"Müller"`` and ``"Mueller"`` tokenize identically, and empty tokens are
    dropped. Splitting happens on whitespace and the common name separators
    before normalization collapses each token to ``[a-z0-9]``.
    """
    return [tok for raw in _TOKEN_SPLIT.split(name) if (tok := normalize(raw))]


def generic_tokens(
    names: Sequence[str],
    *,
    min_df: int = DEFAULT_MIN_GENERIC_DF,
    descriptors: frozenset[str] = ORG_DESCRIPTORS,
) -> frozenset[str]:
    """The generic-token set for a name corpus: descriptors ∪ legal forms ∪
    tokens whose document frequency across ``names`` is ``>= min_df``.

    Document frequency counts each name once per distinct token (so a token
    repeated within one name is not double-counted). The result is what
    :func:`distinctive_stem` strips away.
    """
    document_frequency: Counter[str] = Counter()
    for name in names:
        document_frequency.update(set(tokenize(name)))
    frequent = {tok for tok, df in document_frequency.items() if df >= min_df}
    return frozenset(descriptors) | frozenset(LEGAL_SUFFIXES) | frozenset(frequent)


def distinctive_stem(name: str, generic: frozenset[str]) -> str:
    """The name reduced to its non-generic tokens, space-joined in order.

    ``""`` when every token is generic — such a name carries no distinctive
    signal and is never proposed for a merge.
    """
    return " ".join(tok for tok in tokenize(name) if tok not in generic)


def _embeddable_stems(
    named: Sequence[tuple[str, str]], min_df: int, descriptors: frozenset[str]
) -> list[tuple[str, str]]:
    """``(node_id, distinctive_stem)`` for the candidates that carry a stem.

    Names whose every token is generic drop out — they have no identity signal
    and are never embedded or proposed for a merge.
    """
    candidates = list(named)
    generic = generic_tokens(
        [name for _, name in candidates], min_df=min_df, descriptors=descriptors
    )
    return [
        (node_id, stem)
        for node_id, name in candidates
        if (stem := distinctive_stem(name, generic))
    ]


def _proposals_from_pairs(
    stems: dict[str, str],
    pairs: Iterable[tuple[str, str, float]],
    *,
    threshold: float,
    model_name: str,
) -> list[Resolution]:
    """Build deduplicated, sorted :class:`Resolution`\\s from ``(a, b, cosine)``
    neighbour triples at/above ``threshold``. The two embedding backends differ
    only in how they produce the triples; the assertion shape is shared here."""
    seen: set[tuple[str, str]] = set()
    proposals: list[Resolution] = []
    for node_id, other_id, score in pairs:
        if other_id == node_id or score < threshold:
            continue
        pair = (node_id, other_id) if node_id < other_id else (other_id, node_id)
        if pair in seen:
            continue
        seen.add(pair)
        left, right = pair
        cosine = float(score)
        proposals.append(
            Resolution(
                node_a=left,
                node_b=right,
                score=cosine,
                confidence=min(1.0, cosine),
                reason=(
                    f"embedding match: stem {stems[left]!r} ~ {stems[right]!r} "
                    f"(cosine {cosine:.3f}, model {model_name})"
                ),
            )
        )
    proposals.sort(key=lambda resolution: (resolution.node_a, resolution.node_b))
    return proposals


def propose_semantic_resolutions(
    named: Sequence[tuple[str, str]],
    provider: EmbeddingProvider,
    store: VectorStore | None = None,
    *,
    threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    min_df: int = DEFAULT_MIN_GENERIC_DF,
    descriptors: frozenset[str] = ORG_DESCRIPTORS,
    k: int = 10,
) -> list[Resolution]:
    """Propose same-entity :class:`~tessera.graph.Resolution`\\s from stem cosine,
    embedding via a Python-side ``provider`` into a ``VectorStore``.

    ``named`` is ``(node_id, name)`` for the resolution candidates (e.g.
    ``[(n.id, n.name) for n in graph.name_nodes()]``). Each name's *distinctive
    stem* is embedded and stored (an in-memory cosine KNN by default; a HANA-backed
    store for a GenAI-Hub online path); pairs whose stem cosine is ``>= threshold``
    become additive proposals. The caller adds them to the graph — this function
    mutates nothing. Use :func:`propose_semantic_resolutions_via_index` for the
    HANA-native in-database path (where vectors never enter Python).

    Deterministic given a deterministic ``provider``: candidates are embedded in a
    fixed order, KNN ties break by id (the store's contract), and proposals are
    sorted by ``(node_a, node_b)``.
    """
    embeddable = _embeddable_stems(named, min_df, descriptors)
    if len(embeddable) < 2:
        return []
    stems = dict(embeddable)
    vectors = provider.embed([stem for _, stem in embeddable])
    backing = store if store is not None else InMemoryVectorStore()
    backing.upsert(
        [
            (node_id, vector)
            for (node_id, _), vector in zip(embeddable, vectors, strict=True)
        ]
    )

    def _pairs() -> Iterable[tuple[str, str, float]]:
        for (node_id, _), vector in zip(embeddable, vectors, strict=True):
            # k + 1 because the candidate's own vector is its nearest neighbour.
            for match in backing.query(vector, k + 1):
                yield (node_id, match.id, match.score)

    return _proposals_from_pairs(
        stems, _pairs(), threshold=threshold, model_name=provider.name
    )


def _stem_record(node_id: str, stem: str) -> EvidenceRecord:
    """A throwaway record carrying a stem as text, so a record-shaped semantic
    index (e.g. :class:`~tessera.semantic.HanaSemanticIndex`) can embed it. These
    never surface as evidence — they exist only to drive the in-database embed."""
    return EvidenceRecord(
        id=node_id,
        origin=Origin(
            source="er/stem", locator=Locator(kind="er-stem", parts=()), ingested_at=""
        ),
        text=stem,
    )


def propose_semantic_resolutions_via_index(
    named: Sequence[tuple[str, str]],
    index_builder: Callable[[], _IndexableRetriever],
    *,
    model_name: str,
    threshold: float = DEFAULT_SEMANTIC_THRESHOLD,
    min_df: int = DEFAULT_MIN_GENERIC_DF,
    descriptors: frozenset[str] = ORG_DESCRIPTORS,
    k: int = 10,
) -> list[Resolution]:
    """The HANA-native analogue: propose merges via a record-shaped
    :class:`~tessera.semantic.SemanticRetriever` (the recorded in-database path,
    where vectors never enter Python; ADR 0015).

    Each distinctive stem is wrapped as a throwaway record, indexed by
    ``index_builder()`` (e.g. a :class:`~tessera.semantic.HanaSemanticIndex`), and
    each stem queries its nearest neighbours; pairs at/above ``threshold`` become
    proposals. Same stem-gating, same assertion shape as the provider path —
    only the embed/KNN backend differs. ``model_name`` labels the assertion reason.
    """
    embeddable = _embeddable_stems(named, min_df, descriptors)
    if len(embeddable) < 2:
        return []
    stems = dict(embeddable)
    records = tuple(_stem_record(node_id, stem) for node_id, stem in embeddable)
    index = index_builder()
    index.index(records)

    def _pairs() -> Iterable[tuple[str, str, float]]:
        for node_id, stem in embeddable:
            for record, score in index.retrieve(stem, k + 1):
                yield (node_id, record.id, score)

    return _proposals_from_pairs(
        stems, _pairs(), threshold=threshold, model_name=model_name
    )
