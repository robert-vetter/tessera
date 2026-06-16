"""Scale stress: the trust path stays correct at volume (spec 0049).

The WRITEUP names an honest limitation — "scale behaviour (retrieval quality,
graph performance, ER precision under volume) is untested." This builds a large,
deterministic SALT-shaped graph (180 distinct firms, a planted accented-variant
cohort, hundreds of sales rows) through the **real** engine — the same
KnowledgeGraph, the same ``resolve_entities`` at the 0.85 threshold, the same
multi-step reasoning, the same faithfulness verifier the eval uses — and asserts
the properties that could plausibly break with size:

- **Precision and recall at volume:** distinctive firms stay distinct (180
  clusters from 180 firms) and each accented variant resolves into its firm.
- **Faithfulness holds at volume:** a superlative ranking and a pairwise compare
  over the large graph emit only claims the verifier re-derives.

And it **measures the over-merge risk** the WRITEUP names rather than only
asserting around it: firms sharing a long generic suffix with similar short
stems ("… Logistik GmbH") transitively over-merge at 0.85 — which is exactly why
distinctive master-data tokens matter and why the threshold is a revisitable
knob (ADR 0004). Deterministic (seeded, process-independent) so it reproduces.
"""

from __future__ import annotations

import time

from tessera.business.claims import BUSINESS_CLAIM_SHAPES
from tessera.business.reasoning import compare, find_named_entities, superlative
from tessera.eval.metrics import is_supported
from tessera.graph import Edge, KnowledgeGraph, Node
from tessera.grounding import EvidenceRecord, Locator, Origin

N_ENTITIES = 180
VARIANT_COHORT = 40  # firms that also appear under a merging name variant

# Two pools of mutually dissimilar words. Composed so two firms share at most
# ONE word (plus the legal form), which keeps cross-similarity well under the
# 0.85 merge threshold — the structured "{stem} {industry} GmbH" shape collides
# at volume because the shared generic suffix dominates the name (the documented
# over-merge risk; measured note in spec 0049).
_FIRST = (
    "Zenith",
    "Orbit",
    "Falcon",
    "Crystal",
    "Thunder",
    "Velvet",
    "Saffron",
    "Walnut",
    "Compass",
    "Lantern",
    "Harbor",
    "Summit",
    "Maple",
    "Quartz",
    "Jasper",
)
_SECOND = (
    "Dynamics",
    "Ventures",
    "Holdings",
    "Partners",
    "Networks",
    "Foundry",
    "Logistics",
    "Atelier",
    "Trading",
    "Bureau",
    "Robotics",
    "Textiles",
    "Polymers",
    "Aerospace",
    "Maritime",
)
_FORMS = ("GmbH", "AG", "SE", "KG")

# Acute accents that NFKD-fold back to their base letter, so an accented variant
# normalizes IDENTICALLY to its canonical and must resolve into one entity (the
# real Lumière/Lumiere case, ADR 0004 addendum) — length-independent recall.
_ACCENT = str.maketrans("aeio", "áéíó")


def _canonical(i: int) -> str:
    first = _FIRST[i % len(_FIRST)]
    second = _SECOND[(i // len(_FIRST)) % len(_SECOND)]
    form = _FORMS[i % len(_FORMS)]
    return f"{first} {second} {form}"


def _variant(name: str) -> str:
    return name.translate(_ACCENT)


def _record(node_id: str, table: str, row: int, text: str) -> EvidenceRecord:
    return EvidenceRecord(
        id=node_id,
        origin=Origin(
            source=f"scale/{table}.csv",
            locator=Locator.table_row(table, row),
            ingested_at="2026-06-16",
        ),
        text=text,
    )


def _build_scale_graph() -> tuple[KnowledgeGraph, dict[int, list[str]]]:
    """A large graph built through the real engine; returns it plus the ground
    truth (entity index -> the node ids that should resolve together)."""
    import random

    rng = random.Random(20260616)
    graph = KnowledgeGraph()
    truth: dict[int, list[str]] = {}

    for i in range(N_ENTITIES):
        name = _canonical(i)
        cust_id = f"Customer:{i:04d}"
        graph.add_node(
            Node(
                record=_record(cust_id, "Customer", i, name), kind="Customer", name=name
            )
        )
        truth[i] = [cust_id]
        if i < VARIANT_COHORT:
            addr_id = f"Address:{i:04d}"
            variant = _variant(name)
            graph.add_node(
                Node(
                    record=_record(addr_id, "Address", i, variant),
                    kind="Address",
                    name=variant,
                )
            )
            truth[i].append(addr_id)

    doc = 0
    for i in range(N_ENTITIES):
        for _ in range(rng.randint(1, 4)):
            sid = f"Sales:{doc:05d}"
            doc += 1
            currency = "EUR" if rng.random() < 0.6 else "USD"
            amount = f"{rng.randint(1, 40) * 500}.00"
            graph.add_node(
                Node(
                    record=_record(
                        sid, "Sales", doc, f"Order {sid}: {currency} {amount}"
                    ),
                    kind="Sales",
                    attributes=(("currency", currency), ("net_amount", amount)),
                )
            )
            graph.add_edge(Edge(src=sid, dst=f"Customer:{i:04d}", relation="sold_to"))

    graph.resolve_entities()
    return graph, truth


def test_resolution_precision_and_recall_at_volume() -> None:
    graph, truth = _build_scale_graph()

    # Recall: every planted variant resolved into the same cluster as its firm.
    for ids in truth.values():
        if len(ids) > 1:
            cluster = graph.entity_of(ids[0])
            assert all(nid in cluster for nid in ids)

    # Precision: distinct firms did NOT over-merge — each firm's customer node is
    # the representative of its own cluster, so the number of customer clusters
    # equals the number of firms (no transitive collapse).
    customer_clusters = {
        frozenset(graph.entity_of(f"Customer:{i:04d}")) for i in range(N_ENTITIES)
    }
    assert len(customer_clusters) == N_ENTITIES
    # No mega-cluster swallowing unrelated firms.
    assert (
        max(len(graph.entity_of(f"Customer:{i:04d}")) for i in range(N_ENTITIES)) <= 2
    )


def test_faithfulness_holds_at_volume() -> None:
    graph, _ = _build_scale_graph()
    nodes = {n.id: n for n in graph.nodes}

    # A superlative ranking over the whole large graph.
    ranking = superlative("Which entity has the highest total in EUR?", graph)
    assert ranking.is_grounded
    for claim in ranking.claims:
        assert is_supported(claim, nodes, graph, BUSINESS_CLAIM_SHAPES)

    # A pairwise compare between two firms named in the question.
    a = find_named_entities(f"about {_canonical(3)}", graph)
    b = find_named_entities(f"about {_canonical(7)}", graph)
    assert a and b
    comparison = compare("compare them", a[0], b[0], graph)
    # Either a grounded comparison or an honest refusal (different currencies) —
    # never an unsupported claim.
    for claim in comparison.claims:
        assert is_supported(claim, nodes, graph, BUSINESS_CLAIM_SHAPES)


def test_generic_suffix_firms_over_merge_at_the_threshold() -> None:
    """The measured scale risk (WRITEUP / ADR 0004): distinct firms that share a
    long generic suffix AND have similar short stems cross the 0.85 threshold and
    transitively over-merge. This is exactly why the distinctive master-data
    tokens above matter, and why 0.85 is a documented, revisitable knob — not a
    solved problem. Measured here so the limitation is a number, not a footnote."""
    graph = KnowledgeGraph()
    # Four DISTINCT firms; the shared "Logistik GmbH" suffix dominates the name
    # and the short stems (Granite/Pyrite, Cobalt/Basalt) are themselves similar.
    names = (
        "Granite Logistik GmbH",
        "Pyrite Logistik GmbH",
        "Cobalt Logistik GmbH",
        "Basalt Logistik GmbH",
    )
    for k, name in enumerate(names):
        graph.add_node(
            Node(
                record=_record(f"Customer:{k}", "Customer", k, name),
                kind="Customer",
                name=name,
            )
        )
    graph.resolve_entities()
    clusters = {frozenset(graph.entity_of(f"Customer:{k}")) for k in range(len(names))}
    # The threshold collapses four firms into fewer clusters — a real over-merge.
    assert len(clusters) < len(names)


def test_scale_build_is_fast_enough() -> None:
    """A soft performance signal: building + resolving + reasoning over the
    large graph completes well within a generous bound (it runs in well under a
    second locally; the bound only catches a pathological blow-up)."""
    start = time.perf_counter()
    graph, _ = _build_scale_graph()
    superlative("Which entity has the highest total in USD?", graph)
    elapsed = time.perf_counter() - start
    assert elapsed < 10.0, f"scale path took {elapsed:.2f}s"
