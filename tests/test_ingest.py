"""`tessera ingest <dir>`: declared CSV + Markdown, ER, and ambiguous refusal.

Tests run over the committed public-domain demo corpus (``data/ingest_demo/``)
and over synthetic tmp fixtures for the config/error surface. No network.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tessera.eval.metrics import is_supported
from tessera.graph import KnowledgeGraph
from tessera.grounding import KnowledgeBase
from tessera.ingest.answer import answer_dir, mentioned_names
from tessera.ingest.config import IngestConfig, IngestConfigError, load_config
from tessera.ingest.source import (
    DirSource,
    build_dir_graph,
    build_dir_kb,
)

DEMO = Path(__file__).resolve().parents[1] / "data" / "ingest_demo"


def _demo() -> tuple[IngestConfig, DirSource, KnowledgeGraph, KnowledgeBase]:
    config = load_config(DEMO)
    return config, DirSource(config), build_dir_graph(config), build_dir_kb(config)


# --- ingestion through the one door ------------------------------------------------
def test_demo_ingests_rows_and_document_chunks() -> None:
    _, source, _, _ = _demo()
    records = source.ingest()
    kinds = {r.origin.locator.kind for r in records}
    assert kinds == {"table-row", "doc-span"}
    # 5 cities + 4 regions + the note's chunks.
    table_rows = [r for r in records if r.origin.locator.kind == "table-row"]
    assert len(table_rows) == 9
    assert any(r.id == "city:santa-fe-nm" for r in records)
    for record in records:
        assert record.origin.source.startswith("us-cities-demo/")


def test_fk_edges_and_document_mentions_link() -> None:
    _, source, graph, _ = _demo()
    # The declared city→region edge exists.
    assert ("city:santa-fe-nm", "region:southwest", "in_region") in set(
        source.structural_edges()
    )
    # notes.md mentions cities → at least one document mention resolves.
    assert graph.mentions
    mentioned = {m.node for m in graph.mentions}
    assert "city:santa-fe-nm" in mentioned or "city:columbus-oh" in mentioned


# --- multi-field ER and the ambiguous refusal --------------------------------------
def test_the_two_portlands_stay_distinct() -> None:
    _, _, graph, _ = _demo()
    or_entity = graph.entity_of("city:portland-or")
    me_entity = graph.entity_of("city:portland-me")
    assert or_entity != me_entity  # the state match field kept them apart


def test_ambiguous_name_refuses(tmp_path: Path) -> None:
    config, source, graph, kb = _demo()
    route, answer = answer_dir(
        "Tell me about Portland", graph, kb, source.display_names()
    )
    assert route.kind == "entity"
    assert not answer.is_grounded
    assert "ambiguous" in (answer.refusal or "")
    assert "2 distinct" in (answer.refusal or "")


def test_unambiguous_entity_returns_cited_facts() -> None:
    _, source, graph, kb = _demo()
    route, answer = answer_dir(
        "What do you know about Santa Fe?", graph, kb, source.display_names()
    )
    assert route.kind == "entity"
    assert answer.is_grounded
    sources = {rec.origin.source for claim in answer.claims for rec in claim.support}
    # The city row, its region (FK edge), and the note (mention) are all cited.
    assert "us-cities-demo/cities.csv" in sources
    assert "us-cities-demo/regions.csv" in sources
    assert "us-cities-demo/notes.md" in sources
    # Every claim is a verbatim record rendering → passes the eval's verifier.
    nodes = {node.id: node for node in graph.nodes}
    assert all(is_supported(claim, nodes) for claim in answer.claims)


def test_lexical_fallback_and_zero_overlap_refusal() -> None:
    _, source, graph, kb = _demo()
    names = source.display_names()
    _, hit = answer_dir("Which city is the oldest state capital?", graph, kb, names)
    assert hit.is_grounded  # BM25 finds the note
    _, miss = answer_dir("quantum chromodynamics lattice gauge", graph, kb, names)
    assert not miss.is_grounded  # zero overlap → honest refusal


def test_mentioned_names_matches_whole_phrases_not_substrings() -> None:
    names = {"Portland", "Santa Fe", "ort"}
    hits = mentioned_names("What about Portland today?", names)
    assert "Portland" in hits
    assert "ort" not in hits  # a substring of "Portland" is NOT a match
    assert "Santa Fe" in mentioned_names("I visited Santa Fe", names)
    assert mentioned_names("nothing named here", names) == []


# --- config validation surface -----------------------------------------------------
def _write(tmp_path: Path, toml: str, **files: str) -> Path:
    (tmp_path / "tessera.toml").write_text(toml, "utf-8")
    for name, content in files.items():
        (tmp_path / name.replace("__", ".")).write_text(content, "utf-8")
    return tmp_path


def test_missing_config_is_a_clean_error(tmp_path: Path) -> None:
    with pytest.raises(IngestConfigError, match="no tessera.toml"):
        load_config(tmp_path)


def test_malformed_toml_is_a_clean_error(tmp_path: Path) -> None:
    (tmp_path / "tessera.toml").write_text("this = = broken", "utf-8")
    with pytest.raises(IngestConfigError, match="not valid TOML"):
        load_config(tmp_path)


def test_edge_to_unknown_table_is_rejected(tmp_path: Path) -> None:
    toml = """
name = "x"
[[tables]]
name = "a"
file = "a.csv"
id = "id"
text = "{id}"
  [[tables.edges]]
  column = "ref"
  to = "ghost"
  relation = "r"
"""
    _write(tmp_path, toml)
    with pytest.raises(IngestConfigError, match="unknown table 'ghost'"):
        load_config(tmp_path)


def test_match_field_must_be_declared_attribute(tmp_path: Path) -> None:
    toml = """
name = "x"
[[tables]]
name = "a"
file = "a.csv"
id = "id"
text = "{id}"
match_fields = ["state"]
"""
    _write(tmp_path, toml)
    with pytest.raises(IngestConfigError, match="must also appear in 'attributes'"):
        load_config(tmp_path)


def test_template_attribute_access_is_rejected(tmp_path: Path) -> None:
    toml = """
name = "x"
[[tables]]
name = "a"
file = "a.csv"
id = "id"
text = "{id.__class__}"
"""
    _write(tmp_path, toml, a__csv="id\n1\n")
    config = load_config(tmp_path)
    with pytest.raises(IngestConfigError, match="unsupported field"):
        DirSource(config).ingest()


def test_template_nested_format_spec_field_is_rejected(tmp_path: Path) -> None:
    # A replacement field hidden in a format spec must not bypass the allowlist
    # (str.format's own recursion would otherwise reach attribute traversal).
    toml = """
name = "x"
[[tables]]
name = "a"
file = "a.csv"
id = "id"
text = "{id:{id.__class__}}"
"""
    _write(tmp_path, toml, a__csv="id\n1\n")
    config = load_config(tmp_path)
    with pytest.raises(IngestConfigError, match="unsupported field"):
        DirSource(config).ingest()


def test_file_outside_the_dir_is_refused(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (tmp_path / "secret.csv").write_text("k,v\nx,leaked\n", "utf-8")
    (corpus / "tessera.toml").write_text(
        'name="t"\n[[tables]]\nname="a"\nfile="../secret.csv"\nid="k"\ntext="{k}"\n',
        "utf-8",
    )
    config = load_config(corpus)
    with pytest.raises(IngestConfigError, match="outside the ingested directory"):
        DirSource(config).ingest()


def test_duplicate_id_is_refused(tmp_path: Path) -> None:
    toml = 'name="t"\n[[tables]]\nname="a"\nfile="a.csv"\nid="k"\ntext="{k}"\n'
    _write(tmp_path, toml, a__csv="k,v\ndup,1\ndup,2\n")
    config = load_config(tmp_path)
    with pytest.raises(IngestConfigError, match="duplicate id"):
        DirSource(config).ingest()


def test_missing_template_column_is_named(tmp_path: Path) -> None:
    toml = """
name = "x"
[[tables]]
name = "a"
file = "a.csv"
id = "id"
text = "{id} in {city}"
"""
    _write(tmp_path, toml, a__csv="id,name\n1,alpha\n")
    config = load_config(tmp_path)
    with pytest.raises(IngestConfigError, match="city"):
        DirSource(config).ingest()


def test_nested_spec_render_failure_is_a_clean_error(tmp_path: Path) -> None:
    # A nested-format-spec field whose runtime value is not a valid spec must
    # yield IngestConfigError, not a raw ValueError traceback (review M1).
    toml = """
name = "x"
[[tables]]
name = "a"
file = "a.csv"
id = "id"
text = "{id:{width}}"
"""
    _write(tmp_path, toml, a__csv="id,width\n1,notaspec\n")
    config = load_config(tmp_path)
    with pytest.raises(IngestConfigError, match="could not render"):
        DirSource(config).ingest()


def test_control_sequences_in_content_are_neutralized(tmp_path: Path) -> None:
    # ANSI/OSC escapes in a CSV cell or Markdown line must not reach a claim
    # verbatim (review M2 — the connect door scrubs the same hazard).
    toml = """
name = "x"
[[tables]]
name = "a"
file = "a.csv"
id = "id"
text = "{id}: {label}"
[[documents]]
file = "d.md"
"""
    _write(
        tmp_path,
        toml,
        a__csv="id,label\n1,\x1b[31mred\x1b[0m\x07\n",
        d__md="# Doc\n\nline \x1b[2Jwith escape\n",
    )
    config = load_config(tmp_path)
    for record in DirSource(config).ingest():
        assert "\x1b" not in record.text and "\x07" not in record.text


def test_duplicate_table_name_is_refused(tmp_path: Path) -> None:
    toml = """
name = "x"
[[tables]]
name = "a"
file = "a.csv"
id = "id"
text = "{id}"
[[tables]]
name = "a"
file = "b.csv"
id = "id"
text = "{id}"
"""
    _write(tmp_path, toml, a__csv="id\n1\n", b__csv="id\n2\n")
    with pytest.raises(IngestConfigError, match="duplicate table name"):
        load_config(tmp_path)


def test_reserved_table_name_document_is_refused(tmp_path: Path) -> None:
    toml = """
name = "x"
[[tables]]
name = "document"
file = "a.csv"
id = "id"
text = "{id}"
"""
    _write(tmp_path, toml, a__csv="id\n1\n")
    with pytest.raises(IngestConfigError, match="reserved name"):
        load_config(tmp_path)


def test_glob_does_not_ingest_config_or_table_files(tmp_path: Path) -> None:
    toml = """
name = "x"
[[tables]]
name = "a"
file = "a.csv"
id = "id"
text = "{id}"
[[documents]]
glob = "*"
"""
    _write(tmp_path, toml, a__csv="id\n1\n", notes__md="# real doc\n\nbody\n")
    config = load_config(tmp_path)
    docs = [
        r for r in DirSource(config).ingest() if r.origin.locator.kind == "doc-span"
    ]
    sources = {r.origin.source for r in docs}
    assert sources == {"x/notes.md"}  # not tessera.toml, not a.csv
