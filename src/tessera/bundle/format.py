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

# The minor a CHAIN bundle declares (ADR 0033): minor 1.1 adds the
# `chain-snapshot` closure kind with its `upstream` section. The minor is a
# per-file feature level — a single-decision bundle uses no 1.1 feature and
# keeps declaring 1.0, so the committed challenge artifacts (whose roots are
# public identity) stay byte-stable. Verification never gates on minor; an
# older verifier meeting the unknown closure kind degrades, never
# false-PASSes (the spec-0134 content-not-label rule).
CHAIN_FORMAT_MINOR = 1

# NOTE: redaction (spec 0149) deliberately does NOT bump the minor. `format`
# is itself a manifest leaf, so touching it would move the root — and a
# redacted bundle preserving its original root is the whole point. Redacted
# content is self-describing through its `redacted` markers instead.

# The evidence-closure kind single-decision bundles emit (spec 0131 D4): the
# bundle carries the whole corpus, so whole-graph shapes and omission
# attacks are handled by construction. A verifier that meets an unknown
# kind can only degrade, never upgrade to a re-derived verdict.
CLOSURE_FULL_SNAPSHOT = "full-graph-snapshot"

# The chain closure kind (spec 0143, ADR 0033; format minor 1.1): the corpus
# is derived from other bundles' verifier-passing claims, and those upstream
# bundles are EMBEDDED whole under ``evidence_closure.upstream`` so the file
# stays self-contained. The manifest gains one leaf per upstream, named by
# its root — the chain root commits to the upstream set *and* bytes.
CLOSURE_CHAIN = "chain-snapshot"

# The bundle-native domain name a chain bundle is sealed under. Lives here
# (the format contract) so the emitter and the verifier share it without a
# circular import; the GroundedDomain registry never learns it.
CHAIN_DOMAIN = "chain"

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
_CHAIN_CLOSURE_KEYS = frozenset({"kind", "graph", "kb", "upstream"})
_GRAPH_KEYS = frozenset({"nodes", "edges", "resolutions", "mentions"})


def _closure_keys_for(kind: object) -> frozenset[str]:
    """The exact closure key set a kind may carry — ``upstream`` exists only
    on chain closures, so a full-snapshot bundle cannot smuggle one along."""
    return _CHAIN_CLOSURE_KEYS if kind == CLOSURE_CHAIN else _CLOSURE_KEYS


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


def is_withheld(value: object) -> bool:
    """Whether a section or node was redacted (spec 0149): its content was
    withheld and only the commitment already in the manifest remains.

    A withheld *section* carries the marker alone; a withheld *node* also
    keeps its record id, because citations must still resolve. Anything else
    riding along under the marker is not redaction and is not accepted here.
    """
    if not isinstance(value, dict) or value.get("redacted") is not True:
        return False
    extra = set(value) - {"redacted", "record"}
    if extra:
        return False
    record = value.get("record")
    return record is None or (isinstance(record, dict) and set(record) == {"id"})


def _leaf(value: object, name: str, committed: dict[str, str] | None) -> str:
    """A leaf's digest — or, for withheld content, the commitment the bundle
    was sealed with (spec 0149).

    Taking the stored value here is what preserves the root through
    redaction, and it is safe precisely because withheld content is
    *unverifiable*: no claim can be re-derived from it, so a redacted bundle
    proves LESS, never more. A wrong commitment moves the root and breaks
    any signature or approval made over the original.
    """
    if is_withheld(value):
        if committed is None or name not in committed:
            raise ValueError(
                f"withheld leaf {name!r} has no commitment in the sealed manifest"
            )
        return committed[name]
    return digest(value)


def leaf_manifest(
    bundle: dict[str, object], committed: dict[str, str] | None = None
) -> dict[str, str]:
    """Recompute the leaf manifest from a bundle's content sections.

    One leaf per graph node (``node:<record-id>`` — a tampered record is
    named, not just detected) plus one per remaining sealed section. The
    ``action`` section is a leaf from day one (hashing its literal ``null``
    until unit 0136 fills it); ``signature``/``anchor`` never enter the
    manifest (they attest the root). Raises :class:`ValueError` on a
    malformed shape or a duplicate node id.

    ``committed`` supplies the sealed manifest so **withheld** content
    (spec 0149) contributes its commitment instead of a digest of the
    redaction marker — which is what keeps a redacted bundle's root
    identical to the original's.
    """
    closure = _dict(_get(bundle, "evidence_closure"), "evidence_closure")
    graph_value = _get(closure, "graph")
    graph_withheld = is_withheld(graph_value)
    withheld_marker: dict[str, object] = {"redacted": True}
    graph: dict[str, object] = (
        {
            "nodes": [],
            "edges": withheld_marker,
            "resolutions": withheld_marker,
            "mentions": withheld_marker,
        }
        if graph_withheld
        else _dict(graph_value, "evidence_closure.graph")
    )

    leaves: dict[str, str] = {
        "format": digest(_get(bundle, "format")),
        "engine": digest(_get(bundle, "engine")),
        "result": _leaf(_get(bundle, "result"), "result", committed),
        "action": digest(_get(bundle, "action")),
        # The closure metadata (its declared kind) is hashed too, so tampering
        # the label is at least an integrity break without a re-seal; the
        # verifier additionally decides re-derivability from what is PRESENT,
        # never from this label alone (spec 0134, the downgrade-attack fix).
        "closure.kind": digest(_get(closure, "kind")),
        "kb": _leaf(_get(closure, "kb"), "kb", committed),
        "graph.edges": _leaf(_get(graph, "edges"), "graph.edges", committed),
        "graph.resolutions": _leaf(
            _get(graph, "resolutions"), "graph.resolutions", committed
        ),
        "graph.mentions": _leaf(_get(graph, "mentions"), "graph.mentions", committed),
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
        # A withheld node keeps its id (citations must still resolve) and
        # contributes the commitment it was sealed with (spec 0149).
        leaves[leaf] = _leaf(node, leaf, committed)
    if graph_withheld and committed is not None:
        # The whole graph withheld: every per-record commitment still stands,
        # so the manifest — and the root — are unchanged. Which records existed
        # is public in the manifest; only their content was not shared.
        for name, value in committed.items():
            if name.startswith("node:"):
                leaves[name] = value
    if _get(closure, "kind") == CLOSURE_CHAIN:
        # One leaf per embedded upstream bundle, NAMED by its sealed root
        # (spec 0143 D2): the manifest commits to the upstream set by root and
        # to each upstream's full bytes — the chain is a depth-1 hash-DAG.
        for i, item in enumerate(
            _list(_get(closure, "upstream"), "evidence_closure.upstream")
        ):
            upstream = _dict(item, f"upstream[{i}]")
            integrity = _dict(_get(upstream, "integrity"), f"upstream[{i}].integrity")
            root = _get(integrity, "root")
            if not isinstance(root, str):
                raise ValueError(f"expected a string root at upstream[{i}]")
            leaf = f"upstream:{root}"
            if leaf in leaves:
                raise ValueError(
                    f"duplicate upstream root {root!r} in the chain closure"
                )
            leaves[leaf] = digest(upstream)
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

    # Withheld content contributes the commitment it was sealed with, so a
    # redacted bundle's root recomputes identically (spec 0149).
    recomputed = leaf_manifest(bundle, stored)
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
        extra_closure = set(closure) - _closure_keys_for(closure.get("kind"))
        if extra_closure:
            problems.append(
                f"unexpected evidence_closure key(s) {sorted(extra_closure)}"
            )
        graph = closure.get("graph")
        if isinstance(graph, dict) and not is_withheld(graph):
            extra_graph = set(graph) - _GRAPH_KEYS
            if extra_graph:
                problems.append(f"unexpected graph key(s) {sorted(extra_graph)}")
    return problems
