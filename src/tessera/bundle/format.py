"""The trust-bundle file contract: sections, leaf manifest, root (ADR 0031).

Spec 0133. A ``.tsb`` bundle is one JSON document whose integrity section
carries a leaf manifest (one ``sha256:`` digest per graph node and per
remaining section) and a root over the sorted manifest. This module owns
the shape: which sections exist, how the manifest is computed **from
content**, and how a sealed bundle's stored integrity is re-checked.

What the integrity layer honestly proves: that the file is the file —
which section (down to the record) changed since sealing. Whether the
content is *true* is the verifier's job (unit 0134); the two layers are
reported separately, always.
"""

from __future__ import annotations

from tessera.bundle.canonical import CANONICALIZATION, digest

FORMAT_NAME = "tessera-trust-bundle"
FORMAT_MAJOR = 1
FORMAT_MINOR = 0

# The only evidence-closure kind format major 1 emits (spec 0131 D4): the
# bundle carries the whole corpus, so whole-graph shapes and omission
# attacks are handled by construction. A verifier that meets an unknown
# kind can only degrade, never upgrade to a re-derived verdict.
CLOSURE_FULL_SNAPSHOT = "full-graph-snapshot"

# Sections that are attestations OVER the sealed root (added after sealing)
# and therefore structurally excluded from the manifest they attest.
_UNSEALED_SECTIONS = ("signature", "anchor")

# The exact section sets a format-major-1 bundle carries. The manifest hashes
# individual leaves, not the containing dicts, so an unexpected extra key
# would otherwise ride along unauthenticated (it is neither hashed nor read) —
# a latent trap for any future section. Requiring the sets closes it: the root
# effectively commits to the section *set*, not only the leaf *contents*.
_TOP_LEVEL_KEYS = frozenset(
    {
        "format",
        "engine",
        "result",
        "evidence_closure",
        "integrity",
        "action",
        "signature",
        "anchor",
    }
)
_CLOSURE_KEYS = frozenset({"kind", "graph", "kb"})
_GRAPH_KEYS = frozenset({"nodes", "edges", "resolutions", "mentions"})


def _dict(value: object, key: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"expected an object at {key!r}, got {type(value).__name__}")
    return value


def _list(value: object, key: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"expected a list at {key!r}, got {type(value).__name__}")
    return value


def _get(mapping: dict[str, object], key: str) -> object:
    if key not in mapping:
        raise ValueError(f"missing bundle section {key!r}")
    return mapping[key]


def leaf_manifest(bundle: dict[str, object]) -> dict[str, str]:
    """Recompute the leaf manifest from a bundle's content sections.

    One leaf per graph node (``node:<record-id>`` — a tampered record is
    named, not just detected) plus one per remaining sealed section. The
    ``action`` section is a leaf from day one (hashing its literal ``null``
    until unit 0136 fills it); ``signature``/``anchor`` never enter the
    manifest (they attest the root). Raises :class:`ValueError` on a
    malformed shape or a duplicate node id.
    """
    closure = _dict(_get(bundle, "evidence_closure"), "evidence_closure")
    graph = _dict(_get(closure, "graph"), "evidence_closure.graph")

    leaves: dict[str, str] = {
        "format": digest(_get(bundle, "format")),
        "engine": digest(_get(bundle, "engine")),
        "result": digest(_get(bundle, "result")),
        "action": digest(_get(bundle, "action")),
        # The closure metadata (its declared kind) is hashed too, so tampering
        # the label is at least an integrity break without a re-seal; the
        # verifier additionally decides re-derivability from what is PRESENT,
        # never from this label alone (spec 0134, the downgrade-attack fix).
        "closure.kind": digest(_get(closure, "kind")),
        "kb": digest(_get(closure, "kb")),
        "graph.edges": digest(_get(graph, "edges")),
        "graph.resolutions": digest(_get(graph, "resolutions")),
        "graph.mentions": digest(_get(graph, "mentions")),
    }
    for i, item in enumerate(_list(_get(graph, "nodes"), "nodes")):
        node = _dict(item, f"nodes[{i}]")
        record = _dict(_get(node, "record"), f"nodes[{i}].record")
        record_id = _get(record, "id")
        if not isinstance(record_id, str):
            raise ValueError(f"expected a string node id at nodes[{i}].record.id")
        leaf = f"node:{record_id}"
        if leaf in leaves:
            raise ValueError(f"duplicate node id {record_id!r} in the graph snapshot")
        leaves[leaf] = digest(node)
    return leaves


def compute_root(leaves: dict[str, str]) -> str:
    """The root: sha256 over the canonical bytes of the manifest itself.

    A depth-1 Merkle construction, deliberately (ADR 0031): a v1 bundle
    always travels whole, so every verifier holds every leaf and a deeper
    tree would add machinery without adding a guarantee.
    """
    return digest(leaves)


def seal(bundle: dict[str, object]) -> dict[str, object]:
    """Attach the integrity section (manifest + root) to an unsealed bundle."""
    leaves = leaf_manifest(bundle)
    sealed = dict(bundle)
    sealed["integrity"] = {
        "canonicalization": CANONICALIZATION,
        "leaves": leaves,
        "root": compute_root(leaves),
    }
    return sealed


def integrity_mismatches(bundle: dict[str, object]) -> list[str]:
    """Re-check a sealed bundle's stored integrity against its content.

    Returns human-readable mismatch descriptions, empty when intact:
    a differing leaf names its section (down to ``node:<record-id>``),
    a leaf present only on one side is named as missing/unexpected, a
    stored root that does not recompute reports ``root``, and an unknown
    canonicalization identifier is reported (bytes produced under a
    different recipe cannot be meaningfully compared).
    """
    integrity = _dict(_get(bundle, "integrity"), "integrity")
    problems: list[str] = []

    recipe = _get(integrity, "canonicalization")
    if recipe != CANONICALIZATION:
        return [
            f"canonicalization {recipe!r} is not {CANONICALIZATION!r} — "
            "cannot compare bytes produced under a different recipe"
        ]

    stored_raw = _dict(_get(integrity, "leaves"), "integrity.leaves")
    stored: dict[str, str] = {}
    for name, value in stored_raw.items():
        if not isinstance(value, str):
            problems.append(f"leaf {name!r} is not a digest string")
        else:
            stored[name] = value

    problems.extend(_section_set_problems(bundle))

    recomputed = leaf_manifest(bundle)
    for name in sorted(recomputed.keys() - stored.keys()):
        problems.append(f"missing leaf {name!r}")
    for name in sorted(stored.keys() - recomputed.keys()):
        problems.append(f"unexpected leaf {name!r}")
    for name in sorted(recomputed.keys() & stored.keys()):
        if recomputed[name] != stored[name]:
            problems.append(f"leaf {name!r} does not match its content")

    if _get(integrity, "root") != compute_root(recomputed):
        problems.append("root does not recompute from the content")
    return problems


def _section_set_problems(bundle: dict[str, object]) -> list[str]:
    """The bundle must carry exactly the format-major-1 section set — no extra
    top-level, evidence-closure, or graph keys. The manifest hashes leaves, not
    the containing dicts, so an unexpected key would otherwise pass through
    unauthenticated (neither hashed nor read). Requiring the set makes the root
    commit to the section set, closing that latent trap (the M20/M21 audit
    found it on the reserved ``anchor`` and on injected top-level keys)."""
    problems: list[str] = []
    extra_top = set(bundle) - _TOP_LEVEL_KEYS
    if extra_top:
        problems.append(
            f"unexpected top-level section(s) {sorted(extra_top)} — not "
            "committed by the integrity manifest"
        )
    closure = bundle.get("evidence_closure")
    if isinstance(closure, dict):
        extra_closure = set(closure) - _CLOSURE_KEYS
        if extra_closure:
            problems.append(
                f"unexpected evidence_closure key(s) {sorted(extra_closure)}"
            )
        graph = closure.get("graph")
        if isinstance(graph, dict):
            extra_graph = set(graph) - _GRAPH_KEYS
            if extra_graph:
                problems.append(f"unexpected graph key(s) {sorted(extra_graph)}")
    return problems
