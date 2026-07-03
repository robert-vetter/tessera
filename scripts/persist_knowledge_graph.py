"""One-shot: mirror every committed knowledge graph to SAP HANA Cloud's KG engine.

The staged S2 measurement (spec 0129, ADR 0030). Run it ONCE, by hand, after
the maintainer enables the instance's Triple Store (runbook:
``docs/DEPLOYMENT.md`` → "Knowledge-graph persistence"); it is never part of
the gate, CI, or any answer path.

    set -a; source .env; set +a
    uv run --extra cloud python scripts/persist_knowledge_graph.py

What it does, in order:
1. builds the three committed graphs (business, devex, github_actions);
2. mirrors each into its named graph (``urn:tessera:graph:<name>``) via
   DROP SILENT + batched INSERT DATA over ``SYS.SPARQL_EXECUTE``;
3. runs three recorded SPARQL queries — per-graph triple counts, the
   business battery's resolved pairs (confidence + reason: the reversible
   ER trail, now visible to SAP tooling), and document mentions;
4. prints a paste-ready record block for ``docs/DEPLOYMENT.md``.

Deterministic input, honest output: whatever the engine actually returns is
what gets recorded.
"""

from __future__ import annotations

from tessera.business.knowledge import build_demo_graph
from tessera.devex.knowledge import build_devex_graph, build_github_actions_graph
from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.platform.config import load_config
from tessera.platform.kg import (
    NODE_NS,
    PROP_NS,
    HanaTripleStore,
    graph_iri,
    mirror_graph,
    sparql_drop,
)


def main() -> int:
    config = load_config()
    if not config.hana_host:
        print("HANA_HOST is not set — source .env first (see docs/DEPLOYMENT.md).")
        return 1

    graphs = {
        "business": build_demo_graph(),
        "devex": build_devex_graph(),
        "github_actions": build_github_actions_graph(),
    }
    store = HanaTripleStore(config=config)
    record: list[str] = []
    try:
        # Step 0 — the escape-fidelity canary (spec 0129 review finding 2):
        # SPARQL 1.1 has no UCHAR production in string literals; a strictly
        # conforming processor pre-decodes \\uXXXX over the whole query text,
        # which could corrupt content containing literal backslash-u
        # sequences store-side, invisibly to the in-repo round trip. Store a
        # canary containing exactly that shape, read it back, record verdict.
        # chr(0x2028): explicit, never an invisible literal in source.
        canary_text = "canary: \\u0041 must stay six chars; sep" + chr(0x2028) + "kept"
        canary = KnowledgeGraph()
        canary.add_node(
            Node(
                record=EvidenceRecord(
                    id="Canary:0",
                    origin=Origin(
                        source="spec0129/canary",
                        locator=Locator.table_row("canary", 1),
                        ingested_at="2026-07-03",
                    ),
                    text=canary_text,
                ),
                kind="canary",
            )
        )
        mirror_graph(store, "spec0129-canary", canary)
        got = store.select(
            "SELECT ?text WHERE { GRAPH "
            f"<{graph_iri('spec0129-canary')}> {{ ?s <{PROP_NS}text> ?text }} }}"
        )
        returned = got[0].get("text", "") if got else ""
        verdict = "EXACT" if returned == canary_text else f"DIVERGED: {returned!r}"
        line = f"escape-fidelity canary: {verdict}"
        print(line)
        record.append(line)
        store.execute(sparql_drop("spec0129-canary"))

        for name, graph in graphs.items():
            count = mirror_graph(store, name, graph)
            line = f"mirrored {name}: {count} triples → <{graph_iri(name)}>"
            print(line)
            record.append(line)

        for name in graphs:
            rows = store.select(
                f"SELECT (COUNT(*) AS ?n) WHERE {{ GRAPH <{graph_iri(name)}> "
                f"{{ ?s ?p ?o }} }}"
            )
            # .get: a young engine may label the AS ?n alias differently —
            # the record stays honest instead of crashing mid-run.
            line = f"count({name}) = {rows[0].get('n', '?') if rows else '?'}"
            print(line)
            record.append(line)

        resolved = store.select(
            "SELECT ?a ?b ?confidence ?reason WHERE { GRAPH "
            f"<{graph_iri('business')}> {{ "
            f"?r <{PROP_NS}a> ?a . ?r <{PROP_NS}b> ?b . "
            f"?r <{PROP_NS}confidence> ?confidence . ?r <{PROP_NS}reason> ?reason "
            "} } ORDER BY ?a ?b"
        )
        print(f"business resolved pairs: {len(resolved)}")
        record.append(f"business resolved pairs: {len(resolved)}")
        for row in resolved[:5]:
            a = row["a"].removeprefix(NODE_NS)
            b = row["b"].removeprefix(NODE_NS)
            line = f"  {a} ~ {b} (confidence {row['confidence']})"
            print(line)
            record.append(line)

        # Mentions of RESOLVED entities (spec 0129 decision 7): document
        # chunks referencing a node that participates in a same-entity
        # assertion — the cross-source story, in one SPARQL join.
        mentions = store.select(
            "SELECT ?chunk ?node WHERE { GRAPH "
            f"<{graph_iri('business')}> {{ "
            f"?m <{PROP_NS}chunk> ?chunk . ?m <{PROP_NS}node> ?node . "
            f"{{ ?r <{PROP_NS}a> ?node }} UNION {{ ?r <{PROP_NS}b> ?node }} "
            "} } ORDER BY ?chunk ?node"
        )
        line = f"business mentions of resolved entities: {len(mentions)}"
        print(line)
        record.append(line)
        for row in mentions[:3]:
            chunk = row["chunk"].removeprefix(NODE_NS)
            node = row["node"].removeprefix(NODE_NS)
            line = f"  {chunk} mentions {node}"
            print(line)
            record.append(line)
    finally:
        store.close()

    print("\n--- paste-ready record (docs/DEPLOYMENT.md, with the run date) ---")
    for line in record:
        print(f"# {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
