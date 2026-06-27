"""Semantic retrieval: surface evidence by meaning, with lexical as the fallback.

Two backends produce the same ``(record, score)`` shape behind one
:class:`SemanticRetriever` protocol, so callers (the harness,
:func:`semantic_or_lexical`) never branch on which is in use:

- :class:`HanaSemanticIndex` — HANA Cloud embeds *in-database* via
  ``VECTOR_EMBEDDING`` (the recorded path, spec 0055). Vectors never round-trip
  through Python; one SAP service does embedding + storage + KNN.
- :class:`SemanticIndex` — embeddings from an
  :class:`~tessera.platform.providers.EmbeddingProvider` (e.g. GenAI Hub) stored
  in a :class:`~tessera.platform.vectors.VectorStore` (the documented
  alternative; the seam is not HANA-locked).

The hard line both respect: embeddings decide **which records are surfaced**,
never **what is claimed or how a claim is verified**. The faithfulness verifier
(`eval/metrics.py`) imports nothing from here; a leak-guard test pins that. A 1.0
stays earned by structure, not by a model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from tessera.grounding import EvidenceRecord, KnowledgeBase
from tessera.platform.config import (
    EMBEDDINGS_HANA,
    PlatformConfig,
    load_config,
)
from tessera.platform.providers import EmbeddingProvider, embedding_provider_from_env
from tessera.platform.vectors import (
    Connect,
    HanaVectorStore,
    InMemoryVectorStore,
    VectorStore,
    _Cursor,
    hdbcli_connect,
)
from tessera.retrieval import retrieve

# A model name is interpolated into SQL as a literal (the VECTOR_EMBEDDING third
# argument must be a constant), so it is validated against a strict pattern; the
# text and query are always bound parameters.
_MODEL_PATTERN = re.compile(r"^[A-Za-z0-9_.]+$")


class SemanticRetriever(Protocol):
    """Retrieve evidence by meaning. Both backends satisfy it, so callers depend
    only on this — not on whether HANA or a provider produced the vectors."""

    def retrieve(
        self, question: str, k: int = 5
    ) -> list[tuple[EvidenceRecord, float]]: ...


@dataclass
class SemanticIndex:
    """Provider-embedded view of a record set, queried via a VectorStore.

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
            # Only positively-aligned records are surfaced — the semantic
            # analogue of lexical's "shares a token" (score > 0), so an
            # orthogonal/unrelated record is never returned (precision, ADR 0015).
            if record is not None and match.score > 0:
                hits.append((record, match.score))
        return hits


@dataclass
class HanaSemanticIndex:
    """HANA-native semantic retrieval: HANA itself embeds (``VECTOR_EMBEDDING``).

    Indexing embeds each record's text as a ``DOCUMENT``; a query embeds as a
    ``QUERY`` and ranks by ``COSINE_SIMILARITY`` — all in SQL, so vectors never
    enter Python (spec 0055). The embedding model lives entirely in HANA (the
    instance needs the NLP feature enabled). ``connect`` is injectable so the SQL
    contract is tested against a fake — key-free, offline.
    """

    config: PlatformConfig
    connect: Connect = hdbcli_connect
    table: str = "TESSERA_DOC_VECTORS"
    _records: dict[str, EvidenceRecord] = field(default_factory=dict, init=False)

    def _model(self) -> str:
        model = self.config.hana_embedding_model
        if not _MODEL_PATTERN.match(model):
            raise ValueError(f"unsafe HANA embedding model name: {model!r}")
        return model

    @property
    def _qualified(self) -> str:
        schema = self.config.hana_database.strip()
        return f"{schema}.{self.table}" if schema else self.table

    def _ensure_table(self, cursor: _Cursor) -> None:
        schema = self.config.hana_database.strip()
        if schema:
            cursor.execute(
                "SELECT COUNT(*) FROM SYS.TABLES "
                "WHERE TABLE_NAME = ? AND SCHEMA_NAME = ?",
                [self.table, schema],
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM SYS.TABLES WHERE TABLE_NAME = ?",
                [self.table],
            )
        rows = cursor.fetchall()
        exists = bool(rows) and int(str(rows[0][0])) > 0
        if not exists:
            cursor.execute(
                f"CREATE TABLE {self._qualified} "
                f"(ID NVARCHAR(255) PRIMARY KEY, VEC REAL_VECTOR)",
                [],
            )

    def index(self, records: tuple[EvidenceRecord, ...]) -> None:
        recs = list(records)
        if not recs:
            return
        model = self._model()
        connection = self.connect(self.config)
        try:
            cursor = connection.cursor()
            self._ensure_table(cursor)
            for record in recs:
                cursor.execute(
                    f"UPSERT {self._qualified} (ID, VEC) "
                    f"VALUES (?, VECTOR_EMBEDDING(?, 'DOCUMENT', '{model}')) "
                    f"WITH PRIMARY KEY",
                    [record.id, record.text],
                )
            connection.commit()
            cursor.close()
        finally:
            connection.close()
        self._records = {record.id: record for record in recs}

    def retrieve(self, question: str, k: int = 5) -> list[tuple[EvidenceRecord, float]]:
        model = self._model()
        connection = self.connect(self.config)
        try:
            cursor = connection.cursor()
            cursor.execute(
                f"SELECT TOP {int(k)} ID, "
                f"COSINE_SIMILARITY(VEC, VECTOR_EMBEDDING(?, 'QUERY', '{model}')) "
                f"AS SCORE FROM {self._qualified} ORDER BY SCORE DESC",
                [question],
            )
            rows = cursor.fetchall()
            cursor.close()
        finally:
            connection.close()
        hits: list[tuple[EvidenceRecord, float]] = []
        for row in rows:
            record = self._records.get(str(row[0]))
            score = float(str(row[1]))
            # Positively-aligned records only (precision, ADR 0015).
            if record is not None and score > 0:
                hits.append((record, score))
        return hits


def build_semantic_index(
    records: tuple[EvidenceRecord, ...],
    *,
    config: PlatformConfig | None = None,
    provider: EmbeddingProvider | None = None,
    store: VectorStore | None = None,
) -> SemanticRetriever | None:
    """An indexed semantic retriever, or ``None`` in the default local mode.

    Mode is the ``TESSERA_EMBEDDINGS`` selector: ``hana`` embeds in-database
    (:class:`HanaSemanticIndex`, the recorded path); ``genai-hub`` embeds at
    GenAI Hub and stores in a ``VectorStore`` (the documented alternative);
    ``none`` returns ``None`` so the caller falls back to lexical retrieval.
    ``provider``/``store`` inject the provider path's pieces for offline tests.
    """
    cfg = load_config() if config is None else config

    if cfg.embeddings == EMBEDDINGS_HANA:
        hana_index = HanaSemanticIndex(config=cfg)
        hana_index.index(records)
        return hana_index

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
    index: SemanticRetriever | None = None,
) -> list[tuple[EvidenceRecord, float]]:
    """Semantic hits when an index is present; the lexical BM25 path otherwise.

    The single place the retrieval-strategy decision lives. With no embeddings
    configured ``index`` is ``None`` and behaviour is exactly ADR 0003's
    deterministic lexical retrieval — the offline / CI path, unchanged.
    """
    if index is not None:
        return index.retrieve(question, k)
    return retrieve(question, kb, k)
