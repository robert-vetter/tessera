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

And it pins the **deterministic stem gate** (spec 0070 / ADR 0018): firms sharing
a long generic suffix with distinct short stems ("Granite/Pyrite/… Logistik GmbH")
once transitively over-merged at 0.85 because the shared suffix dominated the
character ratio. The gate now confirms a character match only when the names share
a *distinctive* signal (a non-generic token, or a near-identical distinctive stem),
so the cohort stays four firms — measured here so the cure is a number, not a
footnote.

It also pins the **Milestone-9 cure of the residual the stem gate could not reach**:
two genuinely distinct firms whose names are character-identical (only an address
tells them apart) over-merge under *name-only* resolution, but a second deterministic
signal — the address, passed as ``match_fields`` (spec 0073 / ADR 0019) — splits
them. Each specimen keeps the name-only over-merge as the documented floor in the
same test, so the cure is visible against the limitation. The new floor (kept as a
measured edge in the Milestone-5 tradition) is two distinct firms with the *same*
name **and** the same address — only a registration/tax key would separate them, the
recorded next lever. Deterministic (seeded, process-independent) so it reproduces.
"""

from __future__ import annotations

import time

from tessera.business.claims import BUSINESS_CLAIM_SHAPES
from tessera.business.reasoning import compare, find_named_entities, superlative
from tessera.eval.metrics import is_supported
from tessera.graph import Edge, KnowledgeGraph, Node
from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.resolution import similarity

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


def test_generic_suffix_firms_no_longer_over_merge() -> None:
    """The cured over-merge (spec 0070 / ADR 0018). Four DISTINCT firms share a
    long generic suffix ("… Logistik GmbH") and have short stems that the bare 0.85
    character ratio collapses (Granite~Pyrite 0.865, Cobalt~Basalt 0.889). The stem
    gate recognizes the shared suffix as corpus-generic and confirms a merge only on
    a shared *distinctive* signal — which these firms do not have — so they stay
    four separate entities. This is the milestone's headline ER precision win,
    pinned as a number."""
    graph = KnowledgeGraph()
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
    # Cured: four distinct firms resolve to four distinct entities — no over-merge.
    assert len(clusters) == len(names)
    # And the cure is a *veto*, not an absence of candidates: the two stem-similar
    # pairs clear the 0.85 character threshold, so the bare ratio would have merged
    # them — it is the gate that keeps them apart.
    assert similarity("Granite Logistik GmbH", "Pyrite Logistik GmbH") >= 0.85
    assert similarity("Cobalt Logistik GmbH", "Basalt Logistik GmbH") >= 0.85


def test_character_identical_firms_split_by_address() -> None:
    """Residual 1 cured by multi-field ER (spec 0073 / ADR 0019). Two genuinely
    distinct firms carry the *same* name; name-only resolution shares their
    distinctive token and merges them (the floor the stem gate could not reach), but
    the address — passed as ``match_fields`` — contradicts and splits them. The new
    floor is same name AND same address, which only a registration/tax key would
    separate (the recorded next lever; kept as a measured edge below)."""
    cities = {"Customer:HH": ("Hamburg", "20095"), "Customer:M": ("Munich", "80331")}

    def _build() -> KnowledgeGraph:
        graph = KnowledgeGraph()
        for cid, (city, postal) in cities.items():
            graph.add_node(
                Node(
                    record=_record(cid, "Customer", 0, "Hanseatic Trading GmbH"),
                    kind="Customer",
                    name="Hanseatic Trading GmbH",
                    attributes=(("postal_code", postal), ("city_name", city)),
                )
            )
            addr_id = f"Address:{cid}"
            graph.add_node(
                Node(
                    record=_record(
                        addr_id, "Address", 0, f"Hanseatic Trading GmbH, {city}"
                    ),
                    kind="Address",
                    name=None,
                )
            )
            graph.add_edge(Edge(src=cid, dst=addr_id, relation="has_address"))
        return graph

    # Name-only over-merges — the recorded floor the stem gate could not reach.
    name_only = _build()
    name_only.resolve_entities()
    assert name_only.entity_of("Customer:HH") == name_only.entity_of("Customer:M")

    # Multi-field splits them: the postal codes contradict.
    multi = _build()
    multi.resolve_entities(match_fields=("postal_code", "city_name"))
    assert multi.entity_of("Customer:HH") != multi.entity_of("Customer:M")

    # The new floor: same name AND same address still over-merges — only a
    # registration/tax key would separate them (multi-field ER's remaining lever).
    same_addr = KnowledgeGraph()
    for cid in ("Customer:HH", "Customer:M"):
        same_addr.add_node(
            Node(
                record=_record(cid, "Customer", 0, "Hanseatic Trading GmbH"),
                kind="Customer",
                name="Hanseatic Trading GmbH",
                attributes=(("postal_code", "20095"), ("city_name", "Hamburg")),
            )
        )
    same_addr.resolve_entities(match_fields=("postal_code", "city_name"))
    assert same_addr.entity_of("Customer:HH") == same_addr.entity_of("Customer:M")


def test_two_firm_generic_suffix_split_by_address() -> None:
    """Residual 2 (spec 0070 / ADR 0018) cured by multi-field ER (spec 0073 / ADR
    0019). A suffix is recognized as generic only once it spans ``min_df`` (=3)
    distinct firms, so TWO firms sharing it are below that floor and over-merge on
    name alone (frequency cannot tell them from a two-firm typo pair). Two routes now
    split them: a third distinct firm crosses the genericness floor (the stem gate,
    name-only), OR — for just two firms — a contradicting address (multi-field)."""

    def _resolved(
        names: tuple[str, ...],
        *,
        attrs: list[tuple[tuple[str, str], ...]] | None = None,
        match_fields: tuple[str, ...] = (),
    ) -> KnowledgeGraph:
        graph = KnowledgeGraph()
        for k, name in enumerate(names):
            graph.add_node(
                Node(
                    record=_record(f"Customer:{k}", "Customer", k, name),
                    kind="Customer",
                    name=name,
                    attributes=attrs[k] if attrs else (),
                )
            )
        graph.resolve_entities(match_fields=match_fields)
        return graph

    # Two firms, no address: below the min_df=3 generic floor → name-only over-merges.
    two = _resolved(("Granite Logistik GmbH", "Pyrite Logistik GmbH"))
    assert two.entity_of("Customer:0") == two.entity_of("Customer:1")
    # A third distinct firm with the same suffix crosses the floor → stem gate splits.
    three = _resolved(
        ("Granite Logistik GmbH", "Pyrite Logistik GmbH", "Cobalt Logistik GmbH")
    )
    assert len({frozenset(three.entity_of(f"Customer:{k}")) for k in range(3)}) == 3
    # Multi-field splits even the two-firm case: the addresses contradict.
    split = _resolved(
        ("Granite Logistik GmbH", "Pyrite Logistik GmbH"),
        attrs=[
            (("postal_code", "20095"), ("city_name", "hamburg")),
            (("postal_code", "80331"), ("city_name", "munich")),
        ],
        match_fields=("postal_code", "city_name"),
    )
    assert split.entity_of("Customer:0") != split.entity_of("Customer:1")


def test_scale_build_is_fast_enough() -> None:
    """A soft performance signal: building + resolving + reasoning over the
    large graph completes well within a generous bound (it runs in well under a
    second locally; the bound only catches a pathological blow-up)."""
    start = time.perf_counter()
    graph, _ = _build_scale_graph()
    superlative("Which entity has the highest total in USD?", graph)
    elapsed = time.perf_counter() - start
    assert elapsed < 10.0, f"scale path took {elapsed:.2f}s"
