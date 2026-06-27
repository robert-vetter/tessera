"""Semantic retrieval: surface evidence by meaning, with lexical as the fallback.

This composes the two seams — an :class:`~tessera.platform.providers.EmbeddingProvider`
(text → vector) and a :class:`~tessera.platform.vectors.VectorStore` (store +
KNN) — into a retrieval capability that can bridge vocabulary the lexical BM25
path cannot (the error-class-synonymy miss, ADR 0010 / ADR 0015).

The hard line this module respects: embeddings decide **which records are
surfaced**, never **what is claimed or how a claim is verified**. The
faithfulness verifier (`eval/metrics.py`) imports nothing from here; a leak-guard
test pins that. A 1.0 stays earned by structure, not by a model.

Vertical-neutral: it operates on plain ``EvidenceRecord``s and returns the same
``(record, score)`` shape as :func:`tessera.retrieval.retrieve`, so a caller can
swap one for the other (see :func:`semantic_or_lexical`).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tessera.grounding import EvidenceRecord, KnowledgeBase
from tessera.platform.config import PlatformConfig, load_config
from tessera.platform.providers import EmbeddingProvider, embedding_provider_from_env
from tessera.platform.vectors import (
    HanaVectorStore,
    InMemoryVectorStore,
    VectorStore,
)
from tessera.retrieval import retrieve


@dataclass
class SemanticIndex:
    """An embedded view of a record set, queried by vector similarity.

    Construction embeds nothing; call :meth:`index` once with the records, then
    :meth:`retrieve` per question. Keeps a record handle by id so a KNN match
    (id + score) becomes a ``(record, score)`` pair.
    """

    provider: EmbeddingProvider
    store: VectorStore
    _records: dict[str, EvidenceRecord] = field(default_factory=dict, init=False)

    def index(self, records: tuple[EvidenceRecord, ...]) -> None:
        recs = list(records)
        if not recs:
            return
        vectors = self.provider.embed([r.text for r in recs])
        self.store.upsert([(r.id, v) for r, v in zip(recs, vectors, strict=True)])
        self._records = {r.id: r for r in recs}

    def retrieve(self, question: str, k: int = 5) -> list[tuple[EvidenceRecord, float]]:
        query_vector = self.provider.embed([question])[0]
        hits: list[tuple[EvidenceRecord, float]] = []
        for match in self.store.query(query_vector, k):
            record = self._records.get(match.id)
            if record is not None:
                hits.append((record, match.score))
        return hits


def build_semantic_index(
    records: tuple[EvidenceRecord, ...],
    *,
    config: PlatformConfig | None = None,
    provider: EmbeddingProvider | None = None,
    store: VectorStore | None = None,
) -> SemanticIndex | None:
    """An indexed :class:`SemanticIndex`, or ``None`` in the default local mode.

    Returns ``None`` when no embedding provider is configured — the caller then
    falls back to lexical retrieval. The store defaults to HANA Cloud when
    ``HANA_HOST`` is set, else the portable in-memory backend; both
    ``provider`` and ``store`` are injectable for offline tests.
    """
    cfg = load_config() if config is None else config
    chosen_provider = (
        provider if provider is not None else embedding_provider_from_env(cfg)
    )
    if chosen_provider is None:
        return None
    chosen_store: VectorStore
    if store is not None:
        chosen_store = store
    elif cfg.hana_host:
        chosen_store = HanaVectorStore(config=cfg)
    else:
        chosen_store = InMemoryVectorStore()
    index = SemanticIndex(provider=chosen_provider, store=chosen_store)
    index.index(records)
    return index


def semantic_or_lexical(
    question: str,
    kb: KnowledgeBase,
    *,
    k: int = 5,
    index: SemanticIndex | None = None,
) -> list[tuple[EvidenceRecord, float]]:
    """Semantic hits when an index is present; the lexical BM25 path otherwise.

    The single place the retrieval-strategy decision lives. With no embeddings
    configured ``index`` is ``None`` and behaviour is exactly ADR 0003's
    deterministic lexical retrieval — the offline / CI path, unchanged.
    """
    if index is not None:
        return index.retrieve(question, k)
    return retrieve(question, kb, k)
