"""Knowledge-graph persistence for SAP HANA Cloud's KG engine (spec 0129).

A **mirror, never a source of truth** (ADR 0030): the deterministic
in-process :class:`~tessera.graph.KnowledgeGraph` stays canonical and no
answer path reads from HANA — this module only *exports* it, as RDF triples
in one named graph per corpus, over the engine's ``SYS.SPARQL_EXECUTE``
procedure. Losing the mirror loses nothing; rebuilding it is one call.

The mapping (ADR 0030): **structure as triples, provenance as exact
literals.** Node kinds/names and structural edges become queryable triples;
reified resolutions and mentions carry the reversible assertion trail
(node references, scores, confidences, reasons) into SPARQL-land; evidence
text, origins, and locator/attribute bags ride as byte-exact literals
(locator + attributes as canonical JSON). Numbers serialize as **untyped**
``repr()`` literals — typed ``xsd:double`` invites store-side
canonicalization that would break round-trip fidelity.

Losslessness is a tested contract, not a hope: :func:`graph_to_triples` →
:func:`to_ntriples` → :func:`parse_ntriples` → :func:`graph_from_triples`
reproduces every committed graph tuple-exactly, and the serializer fails
loudly where RDF's set semantics would silently drop data (duplicate
identical edges). The N-Triples parser handles exactly the subset this
module emits — it is the round-trip fixture, not a general RDF reader.

``hdbcli`` stays the lazy, opt-in ``cloud`` extra (ADR 0015 precedent);
importing this module pulls no driver, and CI stays key-free — the HANA
adapter is contract-tested against a fake connection.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote, unquote

from tessera.graph import Edge, KnowledgeGraph, Mention, Node, Resolution
from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.platform.config import PlatformConfig

# The vocabulary: one small, stable namespace. IRIs embed ids percent-encoded
# (quote with safe="") so any record id / relation name round-trips exactly.
_NS = "urn:tessera:"
GRAPH_NS = f"{_NS}graph:"
NODE_NS = f"{_NS}node:"
PROP_NS = f"{_NS}p:"
REL_NS = f"{_NS}rel:"
RESOLUTION_NS = f"{_NS}resolution:"
MENTION_NS = f"{_NS}mention:"

# Triples per INSERT DATA statement. Log-chunk literals are large; batching
# keeps each SPARQL update comfortably inside procedure-parameter limits.
# Named so the first live run can tune it openly (spec 0129).
INSERT_BATCH_SIZE = 500


@dataclass(frozen=True)
class Iri:
    """An IRI object term."""

    value: str


@dataclass(frozen=True)
class Lit:
    """A literal object term (always a plain string — ADR 0030 decision 2)."""

    value: str


Triple = tuple[str, str, "Iri | Lit"]


def graph_iri(corpus: str) -> str:
    return GRAPH_NS + quote(corpus, safe="")


def _node_iri(node_id: str) -> str:
    return NODE_NS + quote(node_id, safe="")


def _prop(name: str) -> str:
    return PROP_NS + name


# --- graph → triples -----------------------------------------------------------


def graph_to_triples(graph: KnowledgeGraph) -> tuple[Triple, ...]:
    """The full graph as ordered triples (nodes, then edges, then the
    additive layers), lossless per ADR 0030.

    Raises ``ValueError`` on duplicate identical edges: RDF's set semantics
    would silently drop one, and silent loss is exactly what this mapping
    refuses (honest failure instead).
    """
    edges = graph.edges
    seen: set[Edge] = set()
    for edge in edges:
        if edge in seen:
            raise ValueError(f"duplicate identical edge cannot be mirrored: {edge}")
        seen.add(edge)

    triples: list[Triple] = []
    for node in graph.nodes:
        subject = _node_iri(node.id)
        record = node.record
        triples.append((subject, _prop("kind"), Lit(node.kind)))
        if node.name is not None:
            triples.append((subject, _prop("name"), Lit(node.name)))
        if node.attributes:
            triples.append(
                (subject, _prop("attributes"), Lit(_json(list(node.attributes))))
            )
        triples.append((subject, _prop("text"), Lit(record.text)))
        triples.append((subject, _prop("source"), Lit(record.origin.source)))
        triples.append((subject, _prop("ingested-at"), Lit(record.origin.ingested_at)))
        locator = record.origin.locator
        triples.append(
            (
                subject,
                _prop("locator"),
                Lit(_json({"kind": locator.kind, "parts": list(locator.parts)})),
            )
        )
    for edge in edges:
        triples.append(
            (
                _node_iri(edge.src),
                REL_NS + quote(edge.relation, safe=""),
                Iri(_node_iri(edge.dst)),
            )
        )
    for index, resolution in enumerate(graph.resolutions):
        subject = f"{RESOLUTION_NS}{index}"
        triples.extend(
            (
                (subject, _prop("a"), Iri(_node_iri(resolution.node_a))),
                (subject, _prop("b"), Iri(_node_iri(resolution.node_b))),
                (subject, _prop("score"), Lit(repr(resolution.score))),
                (subject, _prop("confidence"), Lit(repr(resolution.confidence))),
                (subject, _prop("reason"), Lit(resolution.reason)),
            )
        )
    for index, mention in enumerate(graph.mentions):
        subject = f"{MENTION_NS}{index}"
        triples.extend(
            (
                (subject, _prop("chunk"), Iri(_node_iri(mention.chunk))),
                (subject, _prop("node"), Iri(_node_iri(mention.node))),
                (subject, _prop("confidence"), Lit(repr(mention.confidence))),
                (subject, _prop("reason"), Lit(mention.reason)),
            )
        )
    return tuple(triples)


def _json(value: object) -> str:
    """Canonical JSON for the exact-literal bags (deterministic, unicode kept)."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


# --- N-Triples (the emitted subset) ---------------------------------------------


def _escape(text: str) -> str:
    """N-Triples literal escaping: evidence text is adversarial input to a
    serializer, so everything that could terminate or reshape the literal is
    escaped (spec 0129 decision 4)."""
    out: list[str] = []
    for char in text:
        if char == "\\":
            out.append("\\\\")
        elif char == '"':
            out.append('\\"')
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif ord(char) < 0x20 or ord(char) in (0x85, 0x2028, 0x2029):
            # Control chars, plus the Unicode line/paragraph separators and
            # NEL: grammar-legal raw, but line-sensitive tooling (including
            # Python's own splitlines) treats them as breaks — escaping keeps
            # every serialized triple a single physical line (review finding).
            out.append(f"\\u{ord(char):04X}")
        else:
            out.append(char)
    return "".join(out)


def _unescape(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        char = text[i]
        if char != "\\":
            out.append(char)
            i += 1
            continue
        marker = text[i + 1]
        if marker == "u":
            out.append(chr(int(text[i + 2 : i + 6], 16)))
            i += 6
        else:
            out.append({"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t"}[marker])
            i += 2
    return "".join(out)


def to_ntriples(triples: Sequence[Triple]) -> str:
    lines = []
    for subject, predicate, obj in triples:
        rendered = (
            f"<{obj.value}>" if isinstance(obj, Iri) else f'"{_escape(obj.value)}"'
        )
        lines.append(f"<{subject}> <{predicate}> {rendered} .")
    return "\n".join(lines)


def parse_ntriples(text: str) -> tuple[Triple, ...]:
    """Parse exactly the subset :func:`to_ntriples` emits (the round-trip
    fixture of ADR 0030 — not a general RDF reader). Split on ``\\n`` only —
    the serializer's own joiner; ``splitlines()`` would also split on
    U+2028/U+2029/U+0085, which belt-and-suspenders escaping above now
    prevents from occurring raw anyway (review finding)."""
    triples: list[Triple] = []
    for line in text.split("\n"):
        if not line.strip():
            continue
        assert line.startswith("<"), f"unexpected N-Triples line: {line!r}"
        subject, rest = line[1:].split("> <", 1)
        predicate, rest = rest.split("> ", 1)
        assert rest.endswith(" ."), f"unterminated N-Triples line: {line!r}"
        rendered = rest[:-2]
        obj: Iri | Lit
        if rendered.startswith("<") and rendered.endswith(">"):
            obj = Iri(rendered[1:-1])
        else:
            assert rendered.startswith('"') and rendered.endswith('"')
            obj = Lit(_unescape(rendered[1:-1]))
        triples.append((subject, predicate, obj))
    return tuple(triples)


# --- triples → graph (the round-trip contract) ----------------------------------


def graph_from_triples(triples: Sequence[Triple]) -> KnowledgeGraph:
    """Rebuild a :class:`KnowledgeGraph` from this module's triples —
    tuple-exact against the original (nodes in first-seen subject order,
    edges/resolutions/mentions in emitted order)."""
    node_props: dict[str, dict[str, str]] = {}
    node_order: list[str] = []
    edges: list[Edge] = []
    assertions: dict[str, dict[str, dict[str, str]]] = {"res": {}, "men": {}}

    for subject, predicate, obj in triples:
        if predicate.startswith(REL_NS):
            assert isinstance(obj, Iri)
            edges.append(
                Edge(
                    src=unquote(subject.removeprefix(NODE_NS)),
                    dst=unquote(obj.value.removeprefix(NODE_NS)),
                    relation=unquote(predicate.removeprefix(REL_NS)),
                )
            )
            continue
        key = predicate.removeprefix(PROP_NS)
        value = obj.value  # for IRI-valued props this is the node IRI itself
        if subject.startswith(NODE_NS):
            if subject not in node_props:
                node_props[subject] = {}
                node_order.append(subject)
            node_props[subject][key] = value
        elif subject.startswith(RESOLUTION_NS):
            assertions["res"].setdefault(subject.removeprefix(RESOLUTION_NS), {})[
                key
            ] = value
        elif subject.startswith(MENTION_NS):
            assertions["men"].setdefault(subject.removeprefix(MENTION_NS), {})[key] = (
                value
            )
        else:  # pragma: no cover - the emitted subset has no other subjects
            raise ValueError(f"unknown subject namespace: {subject}")

    graph = KnowledgeGraph()
    for subject in node_order:
        props = node_props[subject]
        locator_bag = json.loads(props["locator"])
        record = EvidenceRecord(
            id=unquote(subject.removeprefix(NODE_NS)),
            origin=Origin(
                source=props["source"],
                locator=Locator(
                    kind=locator_bag["kind"],
                    parts=tuple(
                        (label, value) for label, value in locator_bag["parts"]
                    ),
                ),
                ingested_at=props["ingested-at"],
            ),
            text=props["text"],
        )
        graph.add_node(
            Node(
                record=record,
                kind=props["kind"],
                name=props.get("name"),
                attributes=tuple(
                    (key, value)
                    for key, value in json.loads(props.get("attributes", "[]"))
                ),
            )
        )
    for edge in edges:
        graph.add_edge(edge)
    for index in sorted(assertions["res"], key=int):
        props = assertions["res"][index]
        graph.add_resolution(
            Resolution(
                node_a=unquote(props["a"].removeprefix(NODE_NS)),
                node_b=unquote(props["b"].removeprefix(NODE_NS)),
                score=float(props["score"]),
                confidence=float(props["confidence"]),
                reason=props["reason"],
            )
        )
    for index in sorted(assertions["men"], key=int):
        props = assertions["men"][index]
        graph.add_mention(
            Mention(
                chunk=unquote(props["chunk"].removeprefix(NODE_NS)),
                node=unquote(props["node"].removeprefix(NODE_NS)),
                confidence=float(props["confidence"]),
                reason=props["reason"],
            )
        )
    return graph


# --- SPARQL builders -------------------------------------------------------------


def sparql_drop(corpus: str) -> str:
    """Idempotent mirror step 1: drop the corpus's named graph if present."""
    return f"DROP SILENT GRAPH <{graph_iri(corpus)}>"


def sparql_insert_batches(
    corpus: str, triples: Sequence[Triple], batch_size: int = INSERT_BATCH_SIZE
) -> Iterator[str]:
    """Idempotent mirror step 2: the INSERT DATA statements, batched."""
    iri = graph_iri(corpus)
    for start in range(0, len(triples), batch_size):
        block = to_ntriples(triples[start : start + batch_size])
        yield f"INSERT DATA {{ GRAPH <{iri}> {{\n{block}\n}} }}"


# --- the HANA adapter --------------------------------------------------------------
#
# Typed against minimal protocols (the vectors.py pattern) so the procedure
# contract is checkable without the optional driver; `callproc` is the one
# member vectors' cursor protocol lacks, hence the local definitions.

JSON_RESULTS_HEADER = "Accept: application/sparql-results+json"


class _SparqlCursor(Protocol):
    def callproc(
        self, name: str, parameters: tuple[object, ...]
    ) -> tuple[object, ...]: ...

    def close(self) -> None: ...


class _SparqlConnection(Protocol):
    def cursor(self) -> _SparqlCursor: ...

    def commit(self) -> None: ...

    def close(self) -> None: ...


SparqlConnect = Callable[[PlatformConfig], _SparqlConnection]


def hdbcli_sparql_connect(config: PlatformConfig) -> _SparqlConnection:
    """Open a HANA connection for ``SPARQL_EXECUTE`` via the optional driver
    (lazy import — the ``cloud`` extra is needed only when actually used)."""
    from hdbcli import dbapi  # optional 'cloud' extra; imported only on use

    connection = dbapi.connect(
        address=config.hana_host,
        port=int(config.hana_port or "443"),
        user=config.hana_user,
        password=config.hana_password,
        encrypt=True,
    )
    return connection  # type: ignore[no-any-return]


def _materialize(value: object) -> str:
    """OUT parameters may arrive as LOB handles; read them to text."""
    read = getattr(value, "read", None)
    if callable(read):
        value = read()
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return "" if value is None else str(value)


@dataclass
class HanaTripleStore:
    """SAP HANA Cloud KG engine over ``SYS.SPARQL_EXECUTE(query, headers, ?, ?)``.

    The procedure signature is verified two ways (spec 0127): SAP's own
    tutorial material, and empirically against the live instance (which
    currently answers "No active TripleStore found in landscape" until the
    maintainer enables the Triple Store — the runbook step in
    ``docs/DEPLOYMENT.md``). ``connect`` is injectable so the contract is
    tested against a fake; nothing here is called by any answer path.
    """

    config: PlatformConfig = field(repr=False)  # carries hana_password
    connect: SparqlConnect = hdbcli_sparql_connect
    _connection: _SparqlConnection | None = field(default=None, repr=False)

    def _open(self) -> _SparqlConnection:
        if self._connection is None:
            self._connection = self.connect(self.config)
        return self._connection

    def execute(self, sparql: str, headers: str = "") -> str:
        """Run one SPARQL query/update; returns the raw response body."""
        connection = self._open()
        cursor = connection.cursor()
        try:
            result = cursor.callproc(
                "SYS.SPARQL_EXECUTE", (sparql, headers, None, None)
            )
        finally:
            cursor.close()
        connection.commit()
        return _materialize(result[2])

    def select(self, sparql: str) -> list[dict[str, str]]:
        """Run a SELECT and return its bindings as plain dicts."""
        body = self.execute(sparql, headers=JSON_RESULTS_HEADER)
        payload = json.loads(body)
        return [
            {var: binding[var]["value"] for var in binding}
            for binding in payload.get("results", {}).get("bindings", [])
        ]

    def replace_graph(self, corpus: str, triples: Sequence[Triple]) -> int:
        """The idempotent mirror: drop the corpus graph, insert everything.

        Returns the number of INSERT batches issued (visible progress for the
        one-shot script)."""
        self.execute(sparql_drop(corpus))
        batches = 0
        for statement in sparql_insert_batches(corpus, triples):
            self.execute(statement)
            batches += 1
        return batches

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None


def mirror_graph(store: HanaTripleStore, corpus: str, graph: KnowledgeGraph) -> int:
    """Export one corpus's graph into its named graph on the store; returns
    the triple count (ADR 0030: a mirror — safe to drop and rebuild)."""
    triples = graph_to_triples(graph)
    store.replace_graph(corpus, triples)
    return len(triples)
