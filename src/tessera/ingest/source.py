"""Ingest a declared directory through the engine's one door (spec 0120).

The generic counterpart to ``sources/salt.py`` + ``sources/documents.py``:
the schema knowledge that those modules hard-code in Python comes here from a
declared :class:`~tessera.ingest.config.IngestConfig` instead. Everything else
is the **unchanged** engine — ``read_csv_rows`` + ``Locator.table_row`` for
rows, ``chunk_text`` + ``Locator.doc_span`` for documents,
``resolve_entities(match_fields=…)`` + ``link_document_mentions`` for the graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tessera.connect.scrub import neutralize_controls
from tessera.graph import Edge, KnowledgeGraph, Node
from tessera.grounding import EvidenceRecord, KnowledgeBase, Locator, Origin
from tessera.ingest.config import (
    IngestConfig,
    IngestConfigError,
    TableSpec,
    template_fields,
)
from tessera.ingestion import chunk_text, read_csv_rows
from tessera.resolution import DEFAULT_RESOLUTION_THRESHOLD


def _safe_text(text: str) -> str:
    """Neutralize terminal control sequences in foreign text before it becomes
    a claim (the same hazard the connect door scrubs, ADR 0028): a CSV cell or
    Markdown line carrying ANSI/OSC escapes would otherwise reach a terminal
    verbatim through ``tessera ask``. Line-count preserving, so ``doc-span``
    line ranges stay exact."""
    cleaned, _ = neutralize_controls(text)
    return cleaned


def _within_root(root: Path, relative: str, what: str) -> Path:
    """Resolve ``root/relative`` and require it stay under ``root``.

    A declared ``file`` is semi-trusted (the user authors ``tessera.toml``), but
    a path escaping the corpus dir (``../…`` or an absolute path) would read an
    unrelated file AND stamp a non-resolving ``../`` provenance source — so it
    is refused rather than followed."""
    root_resolved = root.resolve()
    target = (root / relative).resolve()
    if target != root_resolved and root_resolved not in target.parents:
        raise IngestConfigError(
            f"{what} '{relative}' resolves outside the ingested directory "
            f"({root_resolved}); files must live within it."
        )
    return target


def _render(table: TableSpec, row: dict[str, str]) -> str:
    """Render a row's text from its template, erroring clearly on a missing
    column or a value that cannot format (validated field names already bar
    attribute/index access; a nested-format-spec field whose runtime value is
    an invalid spec, e.g. ``{a:{width}}`` with ``width='x'``, would otherwise
    raise a bare ValueError — caught and reported as a config error)."""
    values = {name: row.get(name, "") for name in template_fields(table.text)}
    missing = [name for name in values if name not in row]
    if missing:
        raise IngestConfigError(
            f"table '{table.name}': text template references column(s) {missing} "
            f"absent from {table.file}."
        )
    try:
        rendered = table.text.format(**values)
    except (ValueError, IndexError, KeyError) as error:
        raise IngestConfigError(
            f"table '{table.name}': could not render text template "
            f"{table.text!r} on a row of {table.file}: {error}."
        ) from error
    return _safe_text(rendered)


@dataclass(frozen=True)
class DirSource:
    """Ingester for one configured directory (implements the Ingester contract)."""

    config: IngestConfig

    # --- records ---------------------------------------------------------------
    def _table_rows(self, table: TableSpec) -> list[tuple[str, dict[str, str]]]:
        path = _within_root(self.config.root, table.file, f"table '{table.name}' file")
        if not path.is_file():
            raise IngestConfigError(f"table '{table.name}': file {path} not found.")
        rows: list[tuple[str, dict[str, str]]] = []
        seen: set[str] = set()
        for row in read_csv_rows(path):
            if table.id not in row:
                raise IngestConfigError(
                    f"table '{table.name}': id column '{table.id}' not in {table.file}."
                )
            key = row[table.id]
            if key in seen:
                # The id is a natural key — a duplicate would collapse two rows
                # onto one node and make a citation to it ambiguous. Refuse.
                raise IngestConfigError(
                    f"table '{table.name}': duplicate id {key!r} in {table.file} "
                    f"(column '{table.id}' must be unique)."
                )
            seen.add(key)
            rows.append((key, row))
        return rows

    def ingest(self) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for table in self.config.tables:
            for row_number, (key, row) in enumerate(self._table_rows(table), start=1):
                records.append(
                    EvidenceRecord(
                        id=f"{table.name}:{key}",
                        origin=Origin(
                            source=f"{self.config.name}/{table.file}",
                            locator=Locator.table_row(table.name, row_number),
                            ingested_at=self.config.snapshot_date,
                        ),
                        text=_render(table, row),
                    )
                )
        records.extend(self._document_records())
        return records

    def _document_files(self) -> list[Path]:
        paths: list[Path] = []
        for doc in self.config.documents:
            if doc.file is not None:
                candidate = _within_root(self.config.root, doc.file, "document file")
                if not candidate.is_file():
                    raise IngestConfigError(f"document file {candidate} not found.")
                paths.append(candidate)
            elif doc.glob is not None:
                # root.glob never escapes root; an absolute-pattern glob yields
                # nothing, so documents stay within the corpus dir by construction.
                paths.extend(sorted(self.config.root.glob(doc.glob)))
        # Never ingest the config itself or a declared table file as a document
        # (a broad glob like "*" would otherwise pull tessera.toml and the CSVs
        # in as citable text). Deduplicate while keeping a stable order.
        from tessera.ingest.config import CONFIG_NAME

        excluded = {(self.config.root / CONFIG_NAME).resolve()}
        for table in self.config.tables:
            excluded.add((self.config.root / table.file).resolve())
        seen: set[Path] = set()
        unique: list[Path] = []
        for path in paths:
            resolved = path.resolve()
            if resolved in excluded or resolved in seen:
                continue
            seen.add(resolved)
            unique.append(path)
        return unique

    def _document_records(self) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []
        for path in self._document_files():
            text = path.read_text("utf-8")
            for index, chunk in enumerate(chunk_text(text), start=1):
                records.append(
                    EvidenceRecord(
                        id=f"{path.stem}:chunk{index}",
                        origin=Origin(
                            source=f"{self.config.name}/{path.name}",
                            locator=Locator.doc_span(
                                chunk.start_line, chunk.end_line, index
                            ),
                            ingested_at=self.config.snapshot_date,
                        ),
                        text=_safe_text(chunk.text),
                    )
                )
        return records

    # --- graph inputs ----------------------------------------------------------
    def org_names(self) -> dict[str, str]:
        """Map each name-bearing record id to its declared display name."""
        names: dict[str, str] = {}
        for table in self.config.tables:
            if not table.display_name:
                continue
            for key, row in self._table_rows(table):
                value = row.get(table.display_name)
                if value:
                    names[f"{table.name}:{key}"] = value
        return names

    def node_attributes(self) -> dict[str, tuple[tuple[str, str], ...]]:
        """Declared attribute columns per row, for multi-field ER and display."""
        attrs: dict[str, tuple[tuple[str, str], ...]] = {}
        for table in self.config.tables:
            if not table.attributes:
                continue
            for key, row in self._table_rows(table):
                pairs = tuple(
                    (attr, row[attr]) for attr in table.attributes if row.get(attr)
                )
                if pairs:
                    attrs[f"{table.name}:{key}"] = pairs
        return attrs

    def structural_edges(self) -> list[tuple[str, str, str]]:
        edges: list[tuple[str, str, str]] = []
        for table in self.config.tables:
            if not table.edges:
                continue
            # Read the table once, then apply every edge to each row (not the
            # file once per edge).
            for key, row in self._table_rows(table):
                for edge in table.edges:
                    target = row.get(edge.column)
                    if target:
                        edges.append(
                            (
                                f"{table.name}:{key}",
                                f"{edge.to}:{target}",
                                edge.relation,
                            )
                        )
        return edges

    def match_fields(self) -> tuple[str, ...]:
        """The union of every table's declared match fields (ordered, unique)."""
        ordered: list[str] = []
        for table in self.config.tables:
            for field_name in table.match_fields:
                if field_name not in ordered:
                    ordered.append(field_name)
        return tuple(ordered)

    def display_names(self) -> set[str]:
        return set(self.org_names().values())


# A structured-row locator kind is anything that is not a document chunk.
_CHUNK_KINDS = frozenset({"doc-span"})


def build_dir_kb(config: IngestConfig) -> KnowledgeBase:
    return KnowledgeBase(records=tuple(DirSource(config).ingest()))


def build_dir_graph(
    config: IngestConfig, threshold: float = DEFAULT_RESOLUTION_THRESHOLD
) -> KnowledgeGraph:
    """Assemble the graph the same way the business vertical does: nodes from
    the declared tables (with names + attributes), document nodes, structural
    edges, then multi-field entity resolution and document-mention linking —
    all engine primitives, unchanged."""
    source = DirSource(config)
    org_names = source.org_names()
    node_attrs = source.node_attributes()

    graph = KnowledgeGraph()
    for record in source.ingest():
        if record.origin.locator.kind in _CHUNK_KINDS:
            kind = "document"
        else:
            kind = record.id.split(":", 1)[0]  # the table name
        graph.add_node(
            Node(
                record=record,
                kind=kind,
                name=org_names.get(record.id),
                attributes=node_attrs.get(record.id, ()),
            )
        )
    for src, dst, relation in source.structural_edges():
        graph.add_edge(Edge(src=src, dst=dst, relation=relation))

    graph.resolve_entities(threshold, match_fields=source.match_fields())
    graph.link_document_mentions()
    return graph
