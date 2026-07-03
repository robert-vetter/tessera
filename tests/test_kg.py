"""HANA KG persistence (spec 0129, ADR 0030): losslessness is the contract.

The load-bearing test runs the full round trip — graph → triples →
N-Triples → parse → rebuild — over every committed real graph and demands
tuple-exact equality. Everything else pins the honesty guards: loud failure
on RDF-inexpressible graphs (duplicate edges), injection-safe literal
escaping, determinism, the procedure contract against a fake connection,
and the driver staying out of the default import graph.
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass

import pytest

from tessera.graph import Edge, KnowledgeGraph, Mention, Node, Resolution
from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.platform.config import PlatformConfig
from tessera.platform.kg import (
    INSERT_BATCH_SIZE,
    JSON_RESULTS_HEADER,
    HanaTripleStore,
    graph_from_triples,
    graph_iri,
    graph_to_triples,
    mirror_graph,
    parse_ntriples,
    sparql_drop,
    sparql_insert_batches,
    to_ntriples,
)


def _graphs() -> dict[str, KnowledgeGraph]:
    from tessera.business.knowledge import build_demo_graph
    from tessera.devex.knowledge import build_devex_graph, build_github_actions_graph

    return {
        "business": build_demo_graph(),
        "devex": build_devex_graph(),
        "github_actions": build_github_actions_graph(),
    }


def _assert_equal_graphs(rebuilt: KnowledgeGraph, original: KnowledgeGraph) -> None:
    assert rebuilt.nodes == original.nodes
    assert rebuilt.edges == original.edges
    assert rebuilt.resolutions == original.resolutions
    assert rebuilt.mentions == original.mentions


def test_round_trip_is_tuple_exact_on_every_committed_graph() -> None:
    """ADR 0030's contract: the mirror mapping is lossless on real data."""
    for name, graph in _graphs().items():
        triples = graph_to_triples(graph)
        rebuilt = graph_from_triples(parse_ntriples(to_ntriples(triples)))
        _assert_equal_graphs(rebuilt, graph)
        assert triples, name  # non-vacuous: every corpus produced triples


def _record(record_id: str, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=record_id,
        origin=Origin(
            source="unit/source.csv",
            locator=Locator.table_row("unit", 1),
            ingested_at="2026-07-03",
        ),
        text=text,
    )


def test_adversarial_literals_round_trip_and_stay_inside_their_literal() -> None:
    """Evidence text is adversarial input to a serializer (spec 0129
    decision 4): quote/backslash/newline/control/unicode content — including
    a SPARQL-shaped breakout attempt — must round-trip exactly, and the
    serialized form must contain no unescaped quote from the payload."""
    nasty = '"} DROP GRAPH <urn:tessera:graph:business> ; INSERT DATA {"'
    texts = [
        nasty,
        'line1\nline2\r\ttabbed "quoted" \\backslash\\',
        "control:\x01\x02 bell:\x07",
        "unicode: Müller Logistik — 東京 🚀",
        "separators: a\u2028b\u2029c\u0085d (JS-flavored log text)",
        "backslash-u: \\u0041 stays six characters",
    ]
    graph = KnowledgeGraph()
    for index, text in enumerate(texts):
        graph.add_node(Node(record=_record(f"T:{index}", text), kind="document"))
    triples = graph_to_triples(graph)
    serialized = to_ntriples(triples)
    for line in serialized.splitlines():
        body = line.split("> <", 1)[1].split("> ", 1)[1]
        assert body.endswith(" .")
        inner = body[:-2]
        if inner.startswith('"'):
            # No unescaped quote may terminate the literal early.
            assert inner.endswith('"')
            core = inner[1:-1]
            unescaped_quotes = 0
            i = 0
            while i < len(core):
                if core[i] == "\\":
                    i += 2
                    continue
                if core[i] == '"':
                    unescaped_quotes += 1
                i += 1
            assert unescaped_quotes == 0, line
    # The serialized form must be single-physical-line per triple: no raw
    # LS/PS/NEL may survive escaping (review finding — splitlines() hazards).
    for ch in ("\u2028", "\u2029", "\u0085"):
        assert ch not in serialized
    rebuilt = graph_from_triples(parse_ntriples(serialized))
    _assert_equal_graphs(rebuilt, graph)


def test_ids_and_relations_with_delimiters_round_trip() -> None:
    """Percent-encoded IRIs: ids with spaces, colons, angle brackets, and
    unicode survive; so do relation names."""
    graph = KnowledgeGraph()
    weird_a = "Tab le:row 12/α<>#"
    weird_b = 'Run:R-1042 "quoted"'
    graph.add_node(Node(record=_record(weird_a, "a"), kind="row"))
    graph.add_node(
        Node(
            record=_record(weird_b, "b"),
            kind="Run",
            name="Müller & Söhne",
            attributes=(("status", "failed"), ("näme", "välue")),
        )
    )
    graph.add_edge(Edge(src=weird_a, dst=weird_b, relation="log of/next"))
    graph.add_resolution(
        Resolution(
            node_a=weird_a,
            node_b=weird_b,
            score=0.8461,
            confidence=1.0,
            reason='stem "gate" bridged',
        )
    )
    graph.add_mention(
        Mention(chunk=weird_a, node=weird_b, confidence=0.9, reason="suffix-tolerant")
    )
    rebuilt = graph_from_triples(parse_ntriples(to_ntriples(graph_to_triples(graph))))
    _assert_equal_graphs(rebuilt, graph)
    # Float fidelity via repr round-trip (untyped literals, ADR 0030).
    assert rebuilt.resolutions[0].score == 0.8461


def test_duplicate_identical_edges_fail_loudly() -> None:
    """RDF sets would silently drop a duplicate; the serializer refuses."""
    graph = KnowledgeGraph()
    graph.add_node(Node(record=_record("A", "a"), kind="row"))
    graph.add_node(Node(record=_record("B", "b"), kind="row"))
    graph.add_edge(Edge(src="A", dst="B", relation="rel"))
    graph.add_edge(Edge(src="A", dst="B", relation="rel"))
    with pytest.raises(ValueError, match="duplicate identical edge"):
        graph_to_triples(graph)


def test_serialization_is_deterministic() -> None:
    for name, graph in _graphs().items():
        first = to_ntriples(graph_to_triples(graph))
        second = to_ntriples(graph_to_triples(graph))
        assert first == second, name


def test_sparql_builders_shape() -> None:
    assert sparql_drop("business") == ("DROP SILENT GRAPH <urn:tessera:graph:business>")
    graph = KnowledgeGraph()
    for index in range(3):
        graph.add_node(Node(record=_record(f"N:{index}", f"text {index}"), kind="row"))
    triples = graph_to_triples(graph)
    statements = list(sparql_insert_batches("de mo", triples, batch_size=8))
    # 3 nodes × 5 triples = 15 → 8 + 7 under batch_size=8.
    assert len(statements) == 2
    for statement in statements:
        assert statement.startswith("INSERT DATA { GRAPH <urn:tessera:graph:de%20mo> {")
        assert statement.rstrip().endswith("} }")
    assert graph_iri("de mo") == "urn:tessera:graph:de%20mo"
    assert INSERT_BATCH_SIZE >= 1


# --- the procedure contract, against a fake connection ---------------------------


@dataclass
class _FakeCursor:
    calls: list[tuple[str, tuple[object, ...]]]
    responses: list[str]
    closed: int = 0

    def callproc(self, name: str, parameters: tuple[object, ...]) -> tuple[object, ...]:
        self.calls.append((name, parameters))
        body = self.responses.pop(0) if self.responses else ""
        return (parameters[0], parameters[1], body, "")

    def close(self) -> None:
        self.closed += 1


@dataclass
class _FakeConnection:
    cursor_obj: _FakeCursor
    commits: int = 0
    closes: int = 0

    def cursor(self) -> _FakeCursor:
        return self.cursor_obj

    def commit(self) -> None:
        self.commits += 1

    def close(self) -> None:
        self.closes += 1


def _fake_store(
    responses: list[str] | None = None,
) -> tuple[HanaTripleStore, _FakeCursor, _FakeConnection]:
    cursor = _FakeCursor(calls=[], responses=responses or [])
    connection = _FakeConnection(cursor_obj=cursor)
    store = HanaTripleStore(
        config=PlatformConfig(provider="local"), connect=lambda _config: connection
    )
    return store, cursor, connection


def test_mirror_issues_drop_then_batched_inserts_via_the_procedure() -> None:
    graph = KnowledgeGraph()
    for index in range(3):
        graph.add_node(Node(record=_record(f"N:{index}", f"text {index}"), kind="row"))
    store, cursor, connection = _fake_store()
    count = mirror_graph(store, "business", graph)
    assert count == 15  # 3 nodes × 5 triples
    names = [name for name, _ in cursor.calls]
    assert all(name == "SYS.SPARQL_EXECUTE" for name in names)
    first_query = str(cursor.calls[0][1][0])
    assert first_query.startswith("DROP SILENT GRAPH")
    for _, parameters in cursor.calls[1:]:
        assert str(parameters[0]).startswith("INSERT DATA { GRAPH <")
        assert parameters[1] == ""  # updates pass no Accept header
    assert connection.commits == len(cursor.calls)
    assert cursor.closed == len(cursor.calls)  # cursor closed per call


def test_select_passes_the_json_header_and_parses_bindings() -> None:
    payload = json.dumps(
        {
            "head": {"vars": ["a", "conf"]},
            "results": {
                "bindings": [
                    {
                        "a": {"type": "uri", "value": "urn:tessera:node:X"},
                        "conf": {"type": "literal", "value": "1.0"},
                    }
                ]
            },
        }
    )
    store, cursor, _ = _fake_store(responses=[payload])
    rows = store.select("SELECT ?a ?conf WHERE { ?r ?p ?o }")
    assert rows == [{"a": "urn:tessera:node:X", "conf": "1.0"}]
    ((_, parameters),) = cursor.calls
    assert parameters[1] == JSON_RESULTS_HEADER


def test_lob_out_parameters_are_materialized() -> None:
    class _Lob:
        def read(self) -> bytes:
            return b'{"results": {"bindings": []}}'

    @dataclass
    class _LobCursor(_FakeCursor):
        def callproc(
            self, name: str, parameters: tuple[object, ...]
        ) -> tuple[object, ...]:
            self.calls.append((name, parameters))
            return (parameters[0], parameters[1], _Lob(), "")

    cursor = _LobCursor(calls=[], responses=[])
    connection = _FakeConnection(cursor_obj=cursor)
    store = HanaTripleStore(
        config=PlatformConfig(provider="local"), connect=lambda _c: connection
    )
    assert store.select("SELECT * WHERE { ?s ?p ?o }") == []


def test_default_import_graph_has_no_hdbcli() -> None:
    """The driver stays the opt-in cloud extra (ADR 0015/0030): importing the
    KG module must not pull hdbcli (the test_vectors precedent, subprocess so
    the check is about imports, not this process's state)."""
    code = (
        "import sys; import tessera.platform.kg; "
        "sys.exit(1 if 'hdbcli' in sys.modules else 0)"
    )
    result = subprocess.run([sys.executable, "-c", code], check=False)
    assert result.returncode == 0
