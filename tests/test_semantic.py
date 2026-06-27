"""Semantic retrieval (spec 0054 / ADR 0015): the embed→KNN→record mechanism
bridges vocabulary BM25 cannot, the fallback stays lexical without embeddings,
and the faithfulness verifier imports no embedding module (the standing
invariant).

The stub embedder is a keyword-axis toy — it proves the *mechanism* and that a
model placing synonyms near each other would retrieve the right evidence. The
honest closure of the synonymy is the recorded online run (spec 0057), not this
test.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Sequence

import pytest

from tessera.grounding import EvidenceRecord, KnowledgeBase, Locator, Origin
from tessera.platform.config import load_config
from tessera.platform.vectors import InMemoryVectorStore
from tessera.retrieval import retrieve
from tessera.semantic import (
    HanaSemanticIndex,
    build_semantic_index,
    semantic_or_lexical,
)


class StubEmbeddings:
    """Deterministic keyword-axis embedder — no network. Each axis is a concept;
    a text's vector marks which concepts it mentions, so synonymous phrasings
    that share no lexical token still land on the same axis."""

    name = "stub"

    def __init__(self, axes: list[tuple[str, ...]]) -> None:
        self._axes = axes

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [
            [
                1.0 if any(keyword in text.lower() for keyword in axis) else 0.0
                for axis in self._axes
            ]
            for text in texts
        ]


_AXES = [
    ("not found", "404", "pages has been enabled", "pages not"),  # Pages-deploy
    ("timeout", "timed out"),  # distractor
    ("permission", "denied", "forbidden"),  # distractor
]


def _rec(rid: str, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=rid,
        origin=Origin(
            source=f"specimen/{rid}.log",
            locator=Locator(kind="log-span", parts=(("chunk", "1"),)),
            ingested_at="2026-06-27",
        ),
        text=text,
    )


def _synonymy_records() -> tuple[EvidenceRecord, ...]:
    # a/b/c are three surface forms of ONE root cause that share no lexical token
    # (the real ADR 0010 specimen); d/e are unrelated distractors.
    return (
        _rec("a", "HttpError: Not Found"),
        _rec("b", "status: 404"),
        _rec("c", "Ensure GitHub Pages has been enabled"),
        _rec("d", "Connection timed out after 30s"),
        _rec("e", "Permission denied (publickey)"),
    )


def test_semantic_bridges_synonyms_that_lexical_misses() -> None:
    records = _synonymy_records()
    kb = KnowledgeBase(records=records)
    index = build_semantic_index(
        records,
        config=load_config(env={}),
        provider=StubEmbeddings(_AXES),
        store=InMemoryVectorStore(),
    )
    assert index is not None

    question = "why did the deploy return 404"
    semantic_ids = {r.id for r, _ in index.retrieve(question, k=3)}
    assert semantic_ids == {"a", "b", "c"}  # all three forms surfaced together

    # Lexical BM25 can only reach the form that literally shares the token "404".
    lexical_ids = {r.id for r, score in retrieve(question, kb, k=5) if score > 0}
    assert "b" in lexical_ids
    assert "a" not in lexical_ids and "c" not in lexical_ids


def test_semantic_or_lexical_falls_back_to_bm25_without_index() -> None:
    records = _synonymy_records()
    kb = KnowledgeBase(records=records)
    # No index → identical to the deterministic lexical path (ADR 0003).
    assert semantic_or_lexical("status 404", kb, index=None) == retrieve(
        "status 404", kb, 5
    )


def test_semantic_or_lexical_uses_index_when_present() -> None:
    records = _synonymy_records()
    kb = KnowledgeBase(records=records)
    index = build_semantic_index(
        records,
        config=load_config(env={}),
        provider=StubEmbeddings(_AXES),
        store=InMemoryVectorStore(),
    )
    hits = semantic_or_lexical("not found error", kb, k=3, index=index)
    assert {r.id for r, _ in hits} == {"a", "b", "c"}


def test_build_semantic_index_is_none_in_local_mode() -> None:
    records = (_rec("a", "anything"),)
    assert build_semantic_index(records, config=load_config(env={})) is None


def test_metrics_verifier_imports_no_embedding_module() -> None:
    """Standing invariant: faithfulness is structural. Importing the verifier
    must not pull any embedding/vector/provider module — a 1.0 can never be
    produced by a model. Run in a subprocess so other tests' imports don't
    pollute the check."""
    code = (
        "import sys, tessera.eval.metrics; "
        "banned = {"
        "'tessera.semantic', "
        "'tessera.platform.vectors', "
        "'tessera.platform.providers'"
        "}; "
        "leaked = banned & set(sys.modules); "
        "assert not leaked, sorted(leaked)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


# --- HANA-native retriever (spec 0055): SQL contract against a fake -----------


class _FakeHanaCursor:
    def __init__(self, query_rows: list[tuple[object, ...]]) -> None:
        self.calls: list[tuple[str, list[object]]] = []
        self._query_rows = query_rows
        self._fetch: list[tuple[object, ...]] = []

    def execute(self, operation: str, parameters: Sequence[object]) -> object:
        self.calls.append((operation, list(parameters)))
        if "SYS.TABLES" in operation:
            self._fetch = [(0,)]  # table missing → force CREATE
        elif "COSINE_SIMILARITY" in operation:
            self._fetch = list(self._query_rows)
        else:
            self._fetch = []
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._fetch

    def close(self) -> None:
        return None


class _FakeHanaConnection:
    def __init__(self, cursor: _FakeHanaCursor) -> None:
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self) -> _FakeHanaCursor:
        return self._cursor

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def test_hana_semantic_index_embeds_documents_in_sql() -> None:
    records = _synonymy_records()
    cursor = _FakeHanaCursor(query_rows=[])
    connection = _FakeHanaConnection(cursor)
    config = load_config(
        env={"TESSERA_EMBEDDINGS": "hana", "HANA_HOST": "h", "HANA_DATABASE": "TESSERA"}
    )
    index = HanaSemanticIndex(config=config, connect=lambda _c: connection)
    index.index(records)

    sqls = [sql for sql, _ in cursor.calls]
    assert any("SYS.TABLES" in s for s in sqls)
    assert any(
        "CREATE TABLE TESSERA.TESSERA_DOC_VECTORS" in s and "REAL_VECTOR" in s
        for s in sqls
    )
    upserts = [(s, p) for s, p in cursor.calls if s.startswith("UPSERT")]
    assert len(upserts) == len(records)
    assert "VECTOR_EMBEDDING(?, 'DOCUMENT', 'SAP_NEB.20240715')" in upserts[0][0]
    assert upserts[0][1] == ["a", "HttpError: Not Found"]  # text bound, never in SQL
    assert connection.committed


def test_hana_semantic_index_query_ranks_by_cosine_similarity() -> None:
    records = _synonymy_records()
    cursor = _FakeHanaCursor(query_rows=[("a", 0.93), ("b", 0.88)])
    connection = _FakeHanaConnection(cursor)
    config = load_config(env={"TESSERA_EMBEDDINGS": "hana", "HANA_HOST": "h"})
    index = HanaSemanticIndex(config=config, connect=lambda _c: connection)
    index.index(records)

    hits = index.retrieve("why did the deploy return 404", k=2)
    query_sql = cursor.calls[-1][0]
    assert "SELECT TOP 2 ID" in query_sql
    assert (
        "COSINE_SIMILARITY(VEC, VECTOR_EMBEDDING(?, 'QUERY', 'SAP_NEB.20240715'))"
        in query_sql
    )
    assert "ORDER BY SCORE DESC" in query_sql
    assert [r.id for r, _ in hits] == ["a", "b"]
    assert hits[0][1] == 0.93


def test_hana_semantic_index_rejects_unsafe_model_name() -> None:
    config = load_config(
        env={"HANA_HOST": "h", "HANA_EMBEDDING_MODEL": "evil'; DROP TABLE x;--"}
    )
    index = HanaSemanticIndex(
        config=config,
        connect=lambda _c: _FakeHanaConnection(_FakeHanaCursor([])),
    )
    with pytest.raises(ValueError, match="unsafe HANA embedding model"):
        index.index(_synonymy_records())


def test_build_semantic_index_selects_hana_mode() -> None:
    # Empty records → index() returns before connecting, so no driver is needed.
    index = build_semantic_index(
        (), config=load_config(env={"TESSERA_EMBEDDINGS": "hana", "HANA_HOST": "h"})
    )
    assert isinstance(index, HanaSemanticIndex)
