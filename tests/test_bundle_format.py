"""Tests for the bundle format, sealing, and emission (spec 0133, ADR 0031).

Pinned properties: every emitted bundle's root recomputes from its content;
byte-stability across interpreter hash seeds; tampering names the exact
leaf (down to ``node:<record-id>``); engine pins record the declared shape
identifiers; emission on fresh engines equals the cached ``ground()`` path;
the CLI writes canonical file bytes and reports honestly.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.agent.grounded import ground
from tessera.bundle.canonical import CANONICALIZATION, canonical_bytes, digest
from tessera.bundle.cli import main as bundle_cli
from tessera.bundle.emit import build_bundle, engine_version
from tessera.bundle.format import (
    CLOSURE_FULL_SNAPSHOT,
    FORMAT_MAJOR,
    FORMAT_NAME,
    integrity_mismatches,
    leaf_manifest,
)

_DOMAINS = ("business", "devex", "github_actions")
_GROUNDED = {
    "business": "Compare Müller Logistik and Nordwind Logistik totals.",
    "devex": "Why did run R-1042 fail, and has this happened before?",
    "github_actions": "Why did the pages deploy fail?",
}
_REFUSED = "What is the meaning of life?"

_SECTIONS = (
    "format",
    "engine",
    "result",
    "evidence_closure",
    "integrity",
    "action",
    "signature",
    "anchor",
)


def _result(bundle: dict[str, object]) -> dict[str, object]:
    result = bundle["result"]
    assert isinstance(result, dict)
    return result


# --- emission ---------------------------------------------------------------------


@pytest.mark.parametrize("name", _DOMAINS)
def test_emitted_bundle_has_the_contract_shape_and_recomputes(name: str) -> None:
    bundle = build_bundle(name, _GROUNDED[name])
    assert tuple(sorted(bundle)) == tuple(sorted(_SECTIONS))
    fmt = bundle["format"]
    assert isinstance(fmt, dict)
    assert fmt["name"] == FORMAT_NAME and fmt["major"] == FORMAT_MAJOR
    closure = bundle["evidence_closure"]
    assert isinstance(closure, dict)
    assert closure["kind"] == CLOSURE_FULL_SNAPSHOT
    assert bundle["action"] is None
    assert bundle["signature"] is None
    assert bundle["anchor"] is None
    assert not _result(bundle)["refused"]
    assert integrity_mismatches(bundle) == []


@pytest.mark.parametrize("name", _DOMAINS)
def test_a_refusal_is_bundled_and_sealed_the_same_way(name: str) -> None:
    bundle = build_bundle(name, _REFUSED)
    result = _result(bundle)
    assert result["refused"] and result["refusal"]
    assert result["claims"] == []
    assert integrity_mismatches(bundle) == []


def test_engine_pins_record_declared_shape_identifiers() -> None:
    business = build_bundle("business", _GROUNDED["business"])
    engine = business["engine"]
    assert isinstance(engine, dict)
    assert engine["tessera_version"] == engine_version()
    assert engine["claim_shapes"] == [
        "tessera.business.claims.compare_conclusion",
        "tessera.business.claims.superlative_conclusion",
        "tessera.business.claims.conflict_disclosure",
        "tessera.business.claims.aggregate_recompute",
        "tessera.business.claims.count_match",
        "tessera.business.claims.refuse_to_sum",
    ]
    for name in ("devex", "github_actions"):
        engine_n = build_bundle(name, _GROUNDED[name])["engine"]
        assert isinstance(engine_n, dict)
        assert engine_n["claim_shapes"] == []


@pytest.mark.parametrize("name", _DOMAINS)
def test_fresh_engines_equal_the_cached_ground_path(name: str) -> None:
    """Emission builds its own engines (ADR 0031 §6); the packaged result must
    equal what the cached ``ground()`` path produces for the same inputs."""
    bundle = build_bundle(name, _GROUNDED[name])
    assert _result(bundle) == ground(name, _GROUNDED[name]).to_dict()


def test_byte_stability_across_interpreter_hash_seeds() -> None:
    """The same (domain, question) emitted in two interpreters with different
    hash seeds produces byte-identical files — the portability floor."""
    script = (
        "import sys\n"
        "from tessera.bundle.emit import build_bundle, bundle_bytes\n"
        "data = bundle_bytes(build_bundle('business', sys.argv[1]))\n"
        "sys.stdout.buffer.write(data)\n"
    )
    outputs = []
    for seed in ("0", "424242"):
        proc = subprocess.run(
            [sys.executable, "-c", script, _GROUNDED["business"]],
            capture_output=True,
            check=True,
            env={"PYTHONHASHSEED": seed, "PATH": "/usr/bin:/bin"},
        )
        outputs.append(proc.stdout)
    assert outputs[0] == outputs[1]
    assert outputs[0].endswith(b"\n")


# --- integrity: tampering is named --------------------------------------------------


def _tamper_first_node(bundle: dict[str, object]) -> tuple[dict[str, object], str]:
    tampered = copy.deepcopy(bundle)
    closure = tampered["evidence_closure"]
    assert isinstance(closure, dict)
    graph = closure["graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    node = nodes[0]
    assert isinstance(node, dict)
    record = node["record"]
    assert isinstance(record, dict)
    record["text"] = str(record["text"]) + " [tampered]"
    node_id = record["id"]
    assert isinstance(node_id, str)
    return tampered, node_id


def test_tampering_a_node_names_exactly_that_leaf_and_the_root() -> None:
    bundle = build_bundle("business", _GROUNDED["business"])
    tampered, node_id = _tamper_first_node(bundle)
    problems = integrity_mismatches(tampered)
    assert f"leaf 'node:{node_id}' does not match its content" in problems
    assert "root does not recompute from the content" in problems
    named_nodes = [p for p in problems if p.startswith("leaf 'node:")]
    assert len(named_nodes) == 1  # exactly the tampered record, no other


def test_tampering_the_result_names_the_result_leaf() -> None:
    bundle = build_bundle("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    result = tampered["result"]
    assert isinstance(result, dict)
    result["question"] = "a different question"
    problems = integrity_mismatches(tampered)
    assert "leaf 'result' does not match its content" in problems


def test_missing_and_unexpected_leaves_are_named() -> None:
    bundle = build_bundle("devex", _GROUNDED["devex"])
    tampered = copy.deepcopy(bundle)
    integrity = tampered["integrity"]
    assert isinstance(integrity, dict)
    leaves = integrity["leaves"]
    assert isinstance(leaves, dict)
    del leaves["result"]
    leaves["extra"] = "sha256:" + "0" * 64
    problems = integrity_mismatches(tampered)
    assert "missing leaf 'result'" in problems
    assert "unexpected leaf 'extra'" in problems


def test_unknown_canonicalization_is_refused_not_compared() -> None:
    bundle = build_bundle("devex", _GROUNDED["devex"])
    tampered = copy.deepcopy(bundle)
    integrity = tampered["integrity"]
    assert isinstance(integrity, dict)
    integrity["canonicalization"] = "somebody-elses-recipe-9"
    problems = integrity_mismatches(tampered)
    assert len(problems) == 1 and "cannot compare" in problems[0]


def test_duplicate_node_id_is_rejected() -> None:
    bundle = build_bundle("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    closure = tampered["evidence_closure"]
    assert isinstance(closure, dict)
    graph = closure["graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    nodes.append(copy.deepcopy(nodes[0]))
    with pytest.raises(ValueError, match="duplicate node id"):
        leaf_manifest(tampered)


def test_the_action_section_is_a_leaf_from_day_one() -> None:
    bundle = build_bundle("devex", _GROUNDED["devex"])
    integrity = bundle["integrity"]
    assert isinstance(integrity, dict)
    leaves = integrity["leaves"]
    assert isinstance(leaves, dict)
    assert leaves["action"] == digest(None)
    assert integrity["canonicalization"] == CANONICALIZATION
    # Filling it without resealing is caught (unit 0136 will reseal).
    tampered = copy.deepcopy(bundle)
    tampered["action"] = {"smuggled": True}
    assert "leaf 'action' does not match its content" in integrity_mismatches(tampered)


def test_format_and_closure_kind_are_hashed() -> None:
    """Defense-in-depth (adversarial review, finding 4 / finding 1): editing
    the format section or the closure kind without re-sealing breaks
    integrity, naming the leaf."""
    bundle = build_bundle("business", _GROUNDED["business"])
    integrity = bundle["integrity"]
    assert isinstance(integrity, dict)
    leaves = integrity["leaves"]
    assert isinstance(leaves, dict)
    assert "format" in leaves and "closure.kind" in leaves

    with_minor = copy.deepcopy(bundle)
    fmt = with_minor["format"]
    assert isinstance(fmt, dict)
    fmt["minor"] = 99
    assert "leaf 'format' does not match its content" in integrity_mismatches(
        with_minor
    )

    with_kind = copy.deepcopy(bundle)
    closure = with_kind["evidence_closure"]
    assert isinstance(closure, dict)
    closure["kind"] = "cited-records-only"
    assert "leaf 'closure.kind' does not match its content" in integrity_mismatches(
        with_kind
    )


# --- the CLI -----------------------------------------------------------------------


def test_cli_writes_canonical_bytes_and_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "answer.tsb"
    code = bundle_cli([_GROUNDED["business"], "--domain", "business", "-o", str(out)])
    assert code == 0
    raw = out.read_bytes()
    bundle = json.loads(raw)
    assert raw == canonical_bytes(bundle) + b"\n"
    assert integrity_mismatches(bundle) == []
    stdout = capsys.readouterr().out
    assert "outcome: grounded" in stdout and "root:" in stdout


def test_cli_bundles_a_refusal_with_exit_zero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "refusal.tsb"
    code = bundle_cli([_REFUSED, "--domain", "devex", "-o", str(out)])
    assert code == 0
    assert json.loads(out.read_bytes())["result"]["refused"] is True
    assert "outcome: refusal" in capsys.readouterr().out


def test_cli_rejects_an_unknown_domain(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        bundle_cli(["question", "--domain", "nope"])
    assert excinfo.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_front_door_dispatches_bundle(tmp_path: Path) -> None:
    from tessera.cli import main as front_door

    out = tmp_path / "via-front-door.tsb"
    code = front_door(
        [
            "bundle",
            _GROUNDED["github_actions"],
            "--domain",
            "github_actions",
            "-o",
            str(out),
        ]
    )
    assert code == 0
    assert integrity_mismatches(json.loads(out.read_bytes())) == []
