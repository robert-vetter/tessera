"""Multi-field entity resolution: the two-way address gate (spec 0073 / ADR 0019).

Name-only ER hit a floor (ADR 0018): two distinct firms with the SAME name
over-merge, and a genuine pair whose distinctive tokens are *both* typo'd is vetoed.
A second deterministic signal — the address the source attaches as node attributes —
resolves both, folded into the name decision as a TWO-WAY gate:

  - address DISAGREEMENT vetoes a name-merge (precision: split distinct firms),
  - address AGREEMENT bridges a name-vetoed near-match (recall: same firm).

These pin the engine mechanism on small abstract graphs; the business-graph wiring
(Unit 3) and the measured eval close (Unit 4) build on it. Embedding-free and
deterministic (no cloud, no model).
"""

from __future__ import annotations

from tessera.graph import KnowledgeGraph, Node
from tessera.grounding import EvidenceRecord, Locator, Origin
from tessera.resolution import (
    DEFAULT_RESOLUTION_THRESHOLD as T,
)
from tessera.resolution import (
    compare_match_fields,
    confirm_name_match,
    corpus_generic_tokens,
    similarity,
)

_FIELDS = ("postal_code", "city_name")


def _node(node_id: str, name: str, **attrs: str) -> Node:
    origin = Origin("test.csv", Locator.table_row("T", 1), "2026-06-05")
    rec = EvidenceRecord(id=node_id, origin=origin, text=name)
    return Node(
        record=rec, kind="I_Customer", name=name, attributes=tuple(attrs.items())
    )


def _resolved(
    nodes: list[Node], *, match_fields: tuple[str, ...] = ()
) -> KnowledgeGraph:
    graph = KnowledgeGraph()
    for node in nodes:
        graph.add_node(node)
    graph.resolve_entities(match_fields=match_fields)
    return graph


# --- the field comparator (compare_match_fields) -----------------------------


def test_compare_match_fields_agree_contradict_neutral() -> None:
    assert (
        compare_match_fields(
            {"postal_code": "20095"}, {"postal_code": "20095"}, _FIELDS
        ).verdict
        == "agree"
    )
    assert (
        compare_match_fields(
            {"postal_code": "20095"}, {"postal_code": "80331"}, _FIELDS
        ).verdict
        == "contradict"
    )
    # Absent on one side is NEUTRAL — never read as a contradiction (the none-path).
    assert (
        compare_match_fields({}, {"postal_code": "20095"}, _FIELDS).verdict == "neutral"
    )


def test_compare_match_fields_is_ordered_by_decisiveness() -> None:
    # Postal present on both decides, even though the noisy city would disagree —
    # the clean key is never overridden by a noisy secondary field.
    agree = compare_match_fields(
        {"postal_code": "20095", "city_name": "Hamburg"},
        {"postal_code": "20095", "city_name": "Hamborg"},  # city typo'd
        _FIELDS,
    )
    assert agree.verdict == "agree"
    # Postal absent on one side → fall through to the next field (city).
    contra = compare_match_fields(
        {"city_name": "Hamburg"}, {"city_name": "Munich"}, _FIELDS
    )
    assert contra.verdict == "contradict"


# --- the two-way gate over resolve_entities ----------------------------------


def test_address_contradiction_splits_character_identical_firms() -> None:
    """Residual 1 (ADR 0018): two genuinely distinct firms carry the SAME name; only
    the address tells them apart. Name-only over-merges (the floor); a contradicting
    address splits them."""
    a = _node(
        "c_hh", "Hanseatic Trading GmbH", postal_code="20095", city_name="Hamburg"
    )
    b = _node("c_m", "Hanseatic Trading GmbH", postal_code="80331", city_name="Munich")
    assert similarity("Hanseatic Trading GmbH", "Hanseatic Trading GmbH") >= T
    # Name-only over-merges — the recorded floor.
    name_only = _resolved([a, b])
    assert name_only.entity_of("c_hh") == name_only.entity_of("c_m")
    # Multi-field splits them: the postal codes contradict.
    multi = _resolved([a, b], match_fields=_FIELDS)
    assert multi.entity_of("c_hh") != multi.entity_of("c_m")


def test_address_contradiction_splits_two_firm_generic_suffix() -> None:
    """Residual 2 (ADR 0018): two firms sharing a generic suffix are below the
    min_df=3 floor, so name-only (the suffix is not yet corpus-generic) over-merges;
    different addresses split them."""
    a = _node("c1", "Granite Logistik GmbH", postal_code="20095", city_name="Hamburg")
    b = _node("c2", "Pyrite Logistik GmbH", postal_code="80331", city_name="Munich")
    assert similarity("Granite Logistik GmbH", "Pyrite Logistik GmbH") >= T
    assert _resolved([a, b]).entity_of("c1") == _resolved([a, b]).entity_of("c2")
    multi = _resolved([a, b], match_fields=_FIELDS)
    assert multi.entity_of("c1") != multi.entity_of("c2")


def test_address_agreement_keeps_a_genuine_variant_merge() -> None:
    """A real umlaut/legal-form variant pair with the same address still merges, and
    the agreement is recorded in the assertion reason (inspectable)."""
    a = _node("c1", "Müller Logistik GmbH", postal_code="20095", city_name="Hamburg")
    b = _node("c2", "Mueller Logistik Gmbh", postal_code="20095", city_name="Hamburg")
    graph = _resolved([a, b], match_fields=_FIELDS)
    assert graph.entity_of("c1") == graph.entity_of("c2")
    assert any("postal_code" in r.reason for r in graph.resolutions)


def test_address_bridges_a_stem_vetoed_double_typo() -> None:
    """Residual 3 (ADR 0018): the same firm with BOTH distinctive tokens typo'd. The
    stem gate vetoes on name alone (no shared token, stems too far apart); an agreeing
    address bridges the merge directly, no transitive co-referent needed."""
    generic = corpus_generic_tokens(["Noridc Timber A/S", "Nordic Timbre AS"])
    assert confirm_name_match("Noridc Timber A/S", "Nordic Timbre AS", generic) is None
    assert similarity("Noridc Timber A/S", "Nordic Timbre AS") >= T
    a = _node("c1", "Noridc Timber A/S", postal_code="0150", city_name="Oslo")
    b = _node("c2", "Nordic Timbre AS", postal_code="0150", city_name="Oslo")
    # Name-only leaves them split (the double-typo veto)...
    assert _resolved([a, b]).entity_of("c1") != _resolved([a, b]).entity_of("c2")
    # ...the agreeing address bridges them.
    graph = _resolved([a, b], match_fields=_FIELDS)
    assert graph.entity_of("c1") == graph.entity_of("c2")
    assert any("bridged by address" in r.reason for r in graph.resolutions)


def test_corroboration_is_bounded_to_name_similar_pairs() -> None:
    """The recall arm is bounded: two genuinely different firms at the SAME address
    (a shared building) have dissimilar names (< threshold), so the corroboration arm
    never reaches them — address agreement alone cannot force a merge."""
    a = _node("c1", "Müller Logistik GmbH", postal_code="20095", city_name="Hamburg")
    b = _node("c2", "Nordwind Logistik GmbH", postal_code="20095", city_name="Hamburg")
    assert similarity("Müller Logistik GmbH", "Nordwind Logistik GmbH") < T
    graph = _resolved([a, b], match_fields=_FIELDS)
    assert graph.entity_of("c1") != graph.entity_of("c2")


def test_none_path_ignores_address_attributes() -> None:
    """Backward-compat: with no match_fields, address attributes are not consulted —
    byte-identical to Milestone 8 (the devex / github_actions none-path)."""
    a = _node(
        "c_hh", "Hanseatic Trading GmbH", postal_code="20095", city_name="Hamburg"
    )
    b = _node("c_m", "Hanseatic Trading GmbH", postal_code="80331", city_name="Munich")
    graph = _resolved([a, b])  # match_fields=() — name-only
    assert graph.entity_of("c_hh") == graph.entity_of("c_m")  # over-merges as before
    # The reason is the exact Milestone-8 form: no address note.
    assert graph.resolutions
    assert graph.resolutions[0].reason.startswith("name match: ")
    assert "postal_code" not in graph.resolutions[0].reason


def test_none_path_reason_is_byte_identical_to_milestone_8() -> None:
    """Invariant 1, pinned directly (not just by format): with no match_fields the
    assertion reason is the EXACT Milestone-8 string — a character-level regression
    guard catching a precision/ordering/paren drift the format checks above would
    miss (the unchanged batteries catch it holistically; this catches it locally)."""
    a = _node("c1", "Müller Logistik GmbH", postal_code="20095", city_name="Hamburg")
    b = _node("c2", "Mueller Logistik Gmbh", postal_code="20095", city_name="Hamburg")
    graph = _resolved([a, b])  # match_fields=() — the none-path
    assert graph.resolutions[0].reason == (
        "name match: 'muellerlogistikgmbh' ~ 'muellerlogistikgmbh' "
        "(similarity 1.000; shared distinctive token 'mueller')"
    )


def test_field_match_rejects_postal_substring_collisions() -> None:
    """A review-caught precision hole, pinned: a difflib character ratio called
    genuinely different postal codes near-identical (``"D-20095"`` ~ ``"20095"`` =
    0.909). Exact normalized equality (threshold 1.0) rejects every substring / prefix
    / suffix variant, so the veto arm cannot be fooled into a false AGREE."""
    for pa, pb in [("D-20095", "20095"), ("20095", "200950"), ("020095", "20095")]:
        assert (
            compare_match_fields(
                {"postal_code": pa}, {"postal_code": pb}, _FIELDS
            ).verdict
            == "contradict"
        )
    # Two same-named firms differing only by a prefixed postal must SPLIT, not merge.
    a = _node(
        "c1", "Hanseatic Trading GmbH", postal_code="D-20095", city_name="Hamburg"
    )
    b = _node("c2", "Hanseatic Trading GmbH", postal_code="20095", city_name="Hamburg")
    multi = _resolved([a, b], match_fields=_FIELDS)
    assert multi.entity_of("c1") != multi.entity_of("c2")


def test_stem_vetoed_with_contradicting_address_stays_split() -> None:
    """The 6th gate cell (stem-vetoed + address contradict → veto): a double-typo pair
    whose addresses ALSO contradict stays split. The bridge arm needs *agreement*; a
    contradiction is no bridge — distinguishing the bridge from an unconditional merge
    of stem-vetoed pairs."""
    a = _node("c1", "Noridc Timber A/S", postal_code="0150", city_name="Oslo")
    b = _node("c2", "Nordic Timbre AS", postal_code="8000", city_name="Aarhus")
    graph = _resolved([a, b], match_fields=_FIELDS)
    assert graph.entity_of("c1") != graph.entity_of("c2")
