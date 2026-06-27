"""Vector-store seam (spec 0053 / ADR 0015): the in-memory backend's KNN, the
HANA backend's SQL contract (against a fake connection), and the guarantee that
the default import graph never pulls the optional hdbcli driver."""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence

from tessera.platform.config import load_config
from tessera.platform.vectors import (
    HanaVectorStore,
    InMemoryVectorStore,
    VectorMatch,
    _cosine,
)


def test_in_memory_knn_orders_by_cosine_similarity() -> None:
    store = InMemoryVectorStore()
    store.upsert(
        [
            ("a", [1.0, 0.0]),
            ("b", [0.0, 1.0]),
            ("c", [0.9, 0.1]),
        ]
    )
    matches = store.query([1.0, 0.0], k=2)
    assert [m.id for m in matches] == ["a", "c"]
    assert matches[0].score == 1.0
    assert matches[0].score >= matches[1].score > 0.0


def test_in_memory_is_deterministic_on_ties() -> None:
    """Equal scores break by id ascending — output is stable across hash seeds."""
    store = InMemoryVectorStore()
    store.upsert([("z", [1.0, 0.0]), ("y", [1.0, 0.0]), ("x", [1.0, 0.0])])
    matches = store.query([1.0, 0.0], k=3)
    assert [m.id for m in matches] == ["x", "y", "z"]
    assert {round(m.score, 6) for m in matches} == {1.0}


def test_in_memory_handles_empty_and_oversized_k() -> None:
    store = InMemoryVectorStore()
    assert store.query([1.0, 0.0], k=5) == []
    store.upsert([("only", [1.0, 1.0])])
    assert [m.id for m in store.query([1.0, 1.0], k=5)] == ["only"]


def test_cosine_zero_norm_is_zero() -> None:
    assert _cosine([0.0, 0.0], [1.0, 1.0]) == 0.0


# --- HANA backend: SQL contract against a fake connection --------------------


class _FakeCursor:
    """Records every (sql, params); returns programmed rows by SQL shape."""

    def __init__(self, query_rows: list[tuple[object, ...]]) -> None:
        self.calls: list[tuple[str, list[object]]] = []
        self._query_rows = query_rows
        self._fetch: list[tuple[object, ...]] = []

    def execute(self, operation: str, parameters: Sequence[object]) -> object:
        self.calls.append((operation, list(parameters)))
        if "SYS.TABLES" in operation:
            self._fetch = [(0,)]  # table does not exist yet → force CREATE
        elif "COSINE_SIMILARITY" in operation:
            self._fetch = list(self._query_rows)
        else:
            self._fetch = []
        return None

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._fetch

    def close(self) -> None:
        return None


class _FakeConnection:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self) -> _FakeCursor:
        return self._cursor

    def commit(self) -> None:
        self.committed = True

    def close(self) -> None:
        self.closed = True


def _hana_store(cursor: _FakeCursor) -> tuple[HanaVectorStore, _FakeConnection]:
    connection = _FakeConnection(cursor)
    config = load_config(
        env={
            "HANA_HOST": "h",
            "HANA_USER": "u",
            "HANA_PASSWORD": "p",
            "HANA_DATABASE": "TESSERA",
        }
    )
    return HanaVectorStore(config=config, connect=lambda _c: connection), connection


def test_hana_upsert_creates_table_and_upserts_vectors() -> None:
    cursor = _FakeCursor(query_rows=[])
    store, connection = _hana_store(cursor)
    store.upsert([("rec-1", [0.1, 0.2]), ("rec-2", [0.3, 0.4])])

    sqls = [sql for sql, _ in cursor.calls]
    assert any("SYS.TABLES" in s for s in sqls)
    assert any("CREATE TABLE TESSERA.TESSERA_VECTORS" in s for s in sqls)
    assert any("REAL_VECTOR(2)" in s for s in sqls)  # dim from the first vector

    upserts = [(s, p) for s, p in cursor.calls if s.startswith("UPSERT")]
    assert len(upserts) == 2
    assert "TO_REAL_VECTOR(?)" in upserts[0][0]
    assert "WITH PRIMARY KEY" in upserts[0][0]
    assert upserts[0][1][0] == "rec-1"
    assert json.loads(str(upserts[0][1][1])) == [0.1, 0.2]
    assert connection.committed


def test_hana_query_uses_cosine_similarity_knn() -> None:
    cursor = _FakeCursor(query_rows=[("rec-2", 0.91), ("rec-1", 0.42)])
    store, _ = _hana_store(cursor)
    matches = store.query([0.3, 0.4], k=2)

    query_sql, query_params = cursor.calls[-1]
    assert "COSINE_SIMILARITY(VEC, TO_REAL_VECTOR(?))" in query_sql
    assert "FROM TESSERA.TESSERA_VECTORS" in query_sql
    assert "ORDER BY SCORE DESC" in query_sql
    assert "LIMIT 2" in query_sql
    assert json.loads(str(query_params[0])) == [0.3, 0.4]
    assert matches == [VectorMatch("rec-2", 0.91), VectorMatch("rec-1", 0.42)]


def test_hana_unqualified_table_without_schema() -> None:
    cursor = _FakeCursor(query_rows=[])
    connection = _FakeConnection(cursor)
    config = load_config(env={"HANA_HOST": "h", "HANA_USER": "u"})
    store = HanaVectorStore(config=config, connect=lambda _c: connection)
    store.upsert([("only", [1.0])])
    create = next(s for s, _ in cursor.calls if s.startswith("CREATE TABLE"))
    assert "CREATE TABLE TESSERA_VECTORS" in create  # no schema prefix


def test_hana_upsert_of_nothing_touches_no_connection() -> None:
    calls: list[object] = []

    def exploding_connect(_c: object) -> object:
        calls.append(_c)
        raise AssertionError("empty upsert must not open a connection")

    config = load_config(env={})
    store = HanaVectorStore(config=config, connect=exploding_connect)  # type: ignore[arg-type]
    store.upsert([])
    assert calls == []


def test_default_import_graph_has_no_hdbcli() -> None:
    """The clone-and-run guarantee: importing the vector module and the vertical
    / eval entry points must not pull the optional hdbcli driver."""
    import tessera.business.cli  # noqa: F401
    import tessera.devex.cli  # noqa: F401
    import tessera.eval.cli  # noqa: F401
    import tessera.platform.vectors  # noqa: F401

    assert "hdbcli" not in sys.modules
