"""Parse and validate a ``tessera.toml`` ingestion mapping (ADR 0029).

The config is foreign, hand-authored input, so it is validated eagerly with
clear, user-facing errors that name the offending file and field — never a
raw traceback. Parsing uses the standard library's ``tomllib`` (Python 3.12),
so this adds no dependency and clone-and-run stays intact.
"""

from __future__ import annotations

import string
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_NAME = "tessera.toml"

# Only plain ``{column}`` fields are allowed in a row-text template — no
# attribute (``{x.y}``) or index (``{x[y]}``) access, which over a row dict of
# strings would let a template reach into object internals. A faithful row
# rendering needs nothing more (ADR 0029).
_FORMATTER = string.Formatter()


class IngestConfigError(Exception):
    """A configuration problem with a message meant for the user, verbatim."""


@dataclass(frozen=True)
class EdgeSpec:
    """A foreign key: ``column`` on this table's row → the ``to`` table's id."""

    column: str
    to: str
    relation: str


@dataclass(frozen=True)
class TableSpec:
    name: str
    file: str
    id: str
    text: str
    display_name: str | None = None
    match_fields: tuple[str, ...] = ()
    attributes: tuple[str, ...] = ()
    edges: tuple[EdgeSpec, ...] = ()


@dataclass(frozen=True)
class DocSpec:
    """A document source: an explicit ``file`` or a ``glob`` within the dir."""

    file: str | None = None
    glob: str | None = None


@dataclass(frozen=True)
class IngestConfig:
    root: Path
    name: str
    snapshot_date: str
    tables: tuple[TableSpec, ...]
    documents: tuple[DocSpec, ...] = ()

    def table(self, name: str) -> TableSpec | None:
        return next((t for t in self.tables if t.name == name), None)


def _valid_field(name: str) -> bool:
    """A plain ``{column}`` field: non-empty, not positional (all-digit), and
    only alphanumerics/underscores — so no attribute (``{x.y}``), index
    (``{x[y]}``), or positional (``{0}``/``{}``) access reaches ``str.format``."""
    return bool(name) and not name.isdigit() and name.replace("_", "").isalnum()


def template_fields(template: str) -> list[str]:
    """The plain field names a row-text template references, recursing into
    format specs.

    Nested replacement fields inside a format spec (``{a:>{b}}``) are NOT
    surfaced by a single ``Formatter.parse`` pass, so a naive check would let
    ``{name:{state.__class__}}`` slip through and reach ``str.format`` as an
    attribute traversal / raw ``ValueError``. Recursing closes that.

    Raises :class:`IngestConfigError` on a malformed template or on any field
    that is not a plain ``{column}`` name.
    """
    fields: list[str] = []

    def walk(fragment: str) -> None:
        try:
            parsed = list(_FORMATTER.parse(fragment))
        except ValueError as error:
            raise IngestConfigError(
                f"malformed text template {template!r}: {error}"
            ) from error
        for _literal, field_name, spec, _conv in parsed:
            if field_name is None:
                continue
            if not _valid_field(field_name):
                raise IngestConfigError(
                    f"text template {template!r} uses an unsupported field "
                    f"{field_name!r} — only plain {{column}} names are allowed."
                )
            fields.append(field_name)
            if spec:  # a format spec may itself carry replacement fields
                walk(spec)

    walk(template)
    return fields


def load_config(directory: Path) -> IngestConfig:
    """Load and validate ``<directory>/tessera.toml``."""
    root = Path(directory)
    path = root / CONFIG_NAME
    if not path.is_file():
        raise IngestConfigError(
            f"no {CONFIG_NAME} in {root} — an ingested directory needs a config "
            "(see docs/PILOT.md / ADR 0029 for the format)."
        )
    try:
        raw = tomllib.loads(path.read_text("utf-8"))
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as error:
        raise IngestConfigError(f"{path} is not valid TOML: {error}") from error

    tables = tuple(_table(raw_table, path) for raw_table in _list(raw, "tables", path))
    if not tables:
        raise IngestConfigError(f"{path}: at least one [[tables]] entry is required.")
    _validate_table_names(tables, path)
    _validate_edges(tables, path)
    documents = tuple(_doc(raw_doc, path) for raw_doc in _list(raw, "documents", path))

    return IngestConfig(
        root=root,
        name=str(raw.get("name") or root.name),
        snapshot_date=str(raw.get("snapshot_date") or ""),
        tables=tables,
        documents=documents,
    )


# --- helpers -----------------------------------------------------------------------
def _list(raw: dict[str, object], key: str, path: Path) -> list[dict[str, object]]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, dict) for v in value):
        raise IngestConfigError(f"{path}: [[{key}]] must be an array of tables.")
    return [v for v in value if isinstance(v, dict)]


def _str(raw: dict[str, object], key: str, path: Path, *, where: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value:
        raise IngestConfigError(f"{path}: {where} requires a non-empty '{key}'.")
    return value


def _str_tuple(
    raw: dict[str, object], key: str, path: Path, *, where: str
) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise IngestConfigError(f"{path}: {where} '{key}' must be a list of strings.")
    return tuple(value)


def _table(raw: dict[str, object], path: Path) -> TableSpec:
    name = _str(raw, "name", path, where="a [[tables]] entry")
    where = f"table '{name}'"
    text = _str(raw, "text", path, where=where)
    match_fields = _str_tuple(raw, "match_fields", path, where=where)
    attributes = _str_tuple(raw, "attributes", path, where=where)
    display_name = raw.get("display_name")
    if display_name is not None and not isinstance(display_name, str):
        raise IngestConfigError(f"{path}: {where} 'display_name' must be a string.")
    # match_fields need attributes attached to the node; require them declared.
    missing = [f for f in match_fields if f not in attributes]
    if missing:
        raise IngestConfigError(
            f"{path}: {where} match_fields {missing} must also appear in "
            "'attributes' so they are attached to the node."
        )
    edges = tuple(
        EdgeSpec(
            column=_str(raw_edge, "column", path, where=f"{where} edge"),
            to=_str(raw_edge, "to", path, where=f"{where} edge"),
            relation=_str(raw_edge, "relation", path, where=f"{where} edge"),
        )
        for raw_edge in _list(raw, "edges", path)
    )
    return TableSpec(
        name=name,
        file=_str(raw, "file", path, where=where),
        id=_str(raw, "id", path, where=where),
        text=text,
        display_name=display_name,
        match_fields=match_fields,
        attributes=attributes,
        edges=edges,
    )


def _doc(raw: dict[str, object], path: Path) -> DocSpec:
    file = raw.get("file")
    glob = raw.get("glob")
    if (file is None) == (glob is None):
        raise IngestConfigError(
            f"{path}: each [[documents]] entry needs exactly one of 'file' or 'glob'."
        )
    if file is not None and not isinstance(file, str):
        raise IngestConfigError(f"{path}: [[documents]] 'file' must be a string.")
    if glob is not None and not isinstance(glob, str):
        raise IngestConfigError(f"{path}: [[documents]] 'glob' must be a string.")
    return DocSpec(file=file, glob=glob)


# Node kinds derived from a table name must never collide with a reserved kind:
# document chunks are ``kind="document"``, and the mention-linker treats every
# such node as a document — a table named ``document`` would make its rows
# masquerade as documents.
_RESERVED_TABLE_NAMES = frozenset({"document"})


def _validate_table_names(tables: tuple[TableSpec, ...], path: Path) -> None:
    seen: set[str] = set()
    for table in tables:
        if table.name in _RESERVED_TABLE_NAMES:
            raise IngestConfigError(
                f"{path}: '{table.name}' is a reserved name and cannot be a table."
            )
        if ":" in table.name:
            raise IngestConfigError(
                f"{path}: table name '{table.name}' must not contain ':' "
                "(it prefixes record ids)."
            )
        if table.name in seen:
            raise IngestConfigError(
                f"{path}: duplicate table name '{table.name}' — names must be "
                "unique (they prefix record ids and edge targets)."
            )
        seen.add(table.name)


def _validate_edges(tables: tuple[TableSpec, ...], path: Path) -> None:
    names = {t.name for t in tables}
    for table in tables:
        for edge in table.edges:
            if edge.to not in names:
                raise IngestConfigError(
                    f"{path}: table '{table.name}' has an edge to unknown table "
                    f"'{edge.to}'."
                )
