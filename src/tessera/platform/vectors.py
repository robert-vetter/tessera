"""Vector store seam: a portable in-memory backend + SAP HANA Cloud (ADR 0015).

Embeddings (text → vector) come from an ``EmbeddingProvider`` (providers.py);
this module *stores* those vectors and answers nearest-neighbour queries. Two
backends implement one ``VectorStore`` protocol:

- :class:`InMemoryVectorStore` — pure-stdlib cosine KNN; the portable,
  deterministic backend used by tests and any offline semantic experiment.
- :class:`HanaVectorStore` — SAP HANA Cloud's core vector engine
  (``REAL_VECTOR`` + ``COSINE_SIMILARITY``). The ``hdbcli`` driver is an
  **optional** extra (``uv sync --extra cloud``), imported **lazily** inside the
  connect helper — never at module import — so the default clone-and-run graph
  stays pure-stdlib (guarded by ``tests/test_vectors.py``).

Like the model providers, the HANA backend takes an injected ``connect``
callable, so its SQL contract is verified against a fake connection — key-free
and offline; the live connection is exercised once, at the recorded measurement
(spec 0057).

The store maps ``id → vector`` and returns ids by similarity. It holds **no
claim text**: provenance stays with the records the engine already owns.
Embeddings serve retrieval only (ADR 0015).
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from tessera.platform.config import PlatformConfig


@dataclass(frozen=True)
class VectorMatch:
    """One nearest-neighbour result: a record id and its similarity score."""

    id: str
    score: float


class VectorStore(Protocol):
    """Store vectors by id; return the ``k`` most similar to a query vector."""

    def upsert(self, items: Sequence[tuple[str, Sequence[float]]]) -> None: ...

    def query(self, vector: Sequence[float], k: int) -> list[VectorMatch]: ...


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    """Cosine similarity in [-1, 1]; 0.0 if either vector has zero norm."""
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@dataclass
class InMemoryVectorStore:
    """Pure-stdlib cosine KNN. Deterministic: ties break by id ascending."""

    _vectors: dict[str, tuple[float, ...]] = field(default_factory=dict)

    def upsert(self, items: Sequence[tuple[str, Sequence[float]]]) -> None:
        for id_, vector in items:
            self._vectors[id_] = tuple(float(x) for x in vector)

    def query(self, vector: Sequence[float], k: int) -> list[VectorMatch]:
        scored = [
            VectorMatch(id=id_, score=_cosine(vector, vec))
            for id_, vec in self._vectors.items()
        ]
        # Highest score first; id ascending breaks ties so output is stable
        # regardless of insertion / hash order.
        scored.sort(key=lambda m: (-m.score, m.id))
        return scored[: max(0, k)]


# --- SAP HANA Cloud backend --------------------------------------------------
#
# Typed against minimal DB-API protocols so the SQL contract is checkable
# without the (optional) hdbcli driver present.


class _Cursor(Protocol):
    def execute(self, operation: str, parameters: Sequence[object]) -> object: ...

    def fetchall(self) -> list[tuple[object, ...]]: ...

    def close(self) -> None: ...


class _Connection(Protocol):
    def cursor(self) -> _Cursor: ...

    def commit(self) -> None: ...

    def close(self) -> None: ...


Connect = Callable[[PlatformConfig], _Connection]


def hdbcli_connect(config: PlatformConfig) -> _Connection:
    """Open a HANA Cloud connection via the optional ``hdbcli`` driver.

    Imported here, lazily, so the driver is needed only when the HANA backend is
    actually used — never on a default clone-and-run import.
    """
    from hdbcli import dbapi  # optional 'cloud' extra; imported only on use

    connection = dbapi.connect(
        address=config.hana_host,
        port=int(config.hana_port or "443"),
        user=config.hana_user,
        password=config.hana_password,
        encrypt=True,
    )
    return connection  # type: ignore[no-any-return]


@dataclass
class HanaVectorStore:
    """SAP HANA Cloud vector store (``REAL_VECTOR`` + ``COSINE_SIMILARITY``).

    The table is created on first upsert (dimension taken from the first
    vector). ``connect`` is injectable so the SQL contract is tested against a
    fake; the default opens a real connection via the optional driver.
    """

    config: PlatformConfig
    connect: Connect = hdbcli_connect
    table: str = "TESSERA_VECTORS"

    @property
    def _qualified(self) -> str:
        schema = self.config.hana_database.strip()
        return f"{schema}.{self.table}" if schema else self.table

    def _ensure_table(self, cursor: _Cursor, dim: int) -> None:
        schema = self.config.hana_database.strip()
        # HANA upper-cases unquoted identifiers; match the upper-cased names or
        # the check never finds an existing table (see HanaSemanticIndex).
        if schema:
            cursor.execute(
                "SELECT COUNT(*) FROM SYS.TABLES "
                "WHERE TABLE_NAME = ? AND SCHEMA_NAME = ?",
                [self.table.upper(), schema.upper()],
            )
        else:
            cursor.execute(
                "SELECT COUNT(*) FROM SYS.TABLES WHERE TABLE_NAME = ?",
                [self.table.upper()],
            )
        rows = cursor.fetchall()
        exists = bool(rows) and int(str(rows[0][0])) > 0
        if not exists:
            cursor.execute(
                f"CREATE TABLE {self._qualified} "
                f"(ID NVARCHAR(255) PRIMARY KEY, VEC REAL_VECTOR({dim}))",
                [],
            )

    def upsert(self, items: Sequence[tuple[str, Sequence[float]]]) -> None:
        rows = list(items)
        if not rows:
            return
        dim = len(list(rows[0][1]))
        connection = self.connect(self.config)
        try:
            cursor = connection.cursor()
            self._ensure_table(cursor, dim)
            for id_, vector in rows:
                cursor.execute(
                    f"UPSERT {self._qualified} (ID, VEC) "
                    f"VALUES (?, TO_REAL_VECTOR(?)) WITH PRIMARY KEY",
                    [id_, json.dumps([float(x) for x in vector])],
                )
            connection.commit()
            cursor.close()
        finally:
            connection.close()

    def query(self, vector: Sequence[float], k: int) -> list[VectorMatch]:
        connection = self.connect(self.config)
        try:
            cursor = connection.cursor()
            cursor.execute(
                f"SELECT ID, COSINE_SIMILARITY(VEC, TO_REAL_VECTOR(?)) AS SCORE "
                f"FROM {self._qualified} ORDER BY SCORE DESC LIMIT {int(k)}",
                [json.dumps([float(x) for x in vector])],
            )
            rows = cursor.fetchall()
            cursor.close()
            return [VectorMatch(id=str(r[0]), score=float(str(r[1]))) for r in rows]
        finally:
            connection.close()
