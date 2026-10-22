"""Tests for chained trust bundles (spec 0143, ADR 0033).

The load-bearing promise: one offline `verify` re-executes the WHOLE chain —
every embedded upstream re-verified recursively, every derived record
byte-matched to the upstream claim it cites, the chain answer re-derived.
The centerpiece is the deep-forge theorem test: an attacker with full
re-seal powers at every level, who keeps the chain internally consistent,
is still caught — by the recursion and nothing else.
"""

from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.bundle.chain import (
    CHAIN_CLAIM_SHAPES,
    ChainError,
    build_chain_bundle,
    chain_citation,
)
from tessera.bundle.cli import chain_main
from tessera.bundle.emit import build_bundle, bundle_bytes
from tessera.bundle.format import seal
from tessera.bundle.verify import verify_bundle

REPO = Path(__file__).resolve().parents[1]
HONEST = REPO / "data" / "challenge" / "honest.tsb"
FORGED = REPO / "data" / "challenge" / "forged.tsb"
BRIEF = REPO / "data" / "chain" / "brief.tsb"

RCA_QUESTION = "Why did run R-1042 fail, and has this happened before?"
CHAIN_QUESTION = (
    "What do the verified receipts establish about the run R-1042 failure "
    "and the Müller Logistik and Nordwind Logistik totals?"
)


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _rca() -> dict[str, object]:
    return json.loads(  # type: ignore[no-any-return]
        bundle_bytes(build_bundle("devex", RCA_QUESTION))
    )


def _root(bundle: dict[str, object]) -> str:
    integrity = bundle["integrity"]
    assert isinstance(integrity, dict)
    root = integrity["root"]
    assert isinstance(root, str)
    return root


def _reseal(bundle: dict[str, object]) -> dict[str, object]:
    """Re-seal after a mutation — the realistic attacker recomputes hashes."""
    return seal({k: v for k, v in bundle.items() if k != "integrity"})


@pytest.fixture(scope="module")
def brief() -> dict[str, object]:
    """A fresh chain over [devex RCA, committed honest business bundle] —
    the same construction as the committed demo."""
    return json.loads(  # type: ignore[no-any-return]
        bundle_bytes(build_chain_bundle([_rca(), _load(HONEST)], CHAIN_QUESTION))
    )


# --- the happy path ---------------------------------------------------------------


def test_chain_passes_and_cites_both_upstreams(brief: dict[str, object]) -> None:
    report = verify_bundle(brief)
    assert report.verdict == "PASS" and report.exit_code == 0
    assert len(report.upstreams) == 2
    assert all(u.verdict == "PASS" for u in report.upstreams)
    result = brief["result"]
    assert isinstance(result, dict)
    claims = result["claims"]
    assert isinstance(claims, list)
    cited_roots = {
        e["source"]
        for c in claims
        if isinstance(c, dict)
        for e in c["support"]
        if isinstance(e, dict)
    }
    # The brief genuinely draws on BOTH upstream bundles, not one.
    assert len(cited_roots) == 2


def test_committed_demo_verifies_and_is_byte_identical() -> None:
    """The committed brief PASSes from the file alone, and re-running the
    committed script reproduces it byte-for-byte (no drift, spec 0140's
    pattern)."""
    committed = BRIEF.read_bytes()
    report = verify_bundle(json.loads(committed.decode("utf-8")))
    assert report.verdict == "PASS"

    sys.path.insert(0, str(REPO / "scripts"))
    try:
        from build_chain_demo import build_brief  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    assert bundle_bytes(build_brief()) == committed


def test_report_json_carries_upstreams(brief: dict[str, object]) -> None:
    payload = verify_bundle(brief).to_dict()
    upstreams = payload["upstreams"]
    assert isinstance(upstreams, list) and len(upstreams) == 2
    assert all(u["verdict"] == "PASS" for u in upstreams)


def test_chain_of_chain_depth_two(brief: dict[str, object]) -> None:
    """A chain can cite a chain; verification recurses through both levels."""
    meta = build_chain_bundle(
        [brief], "What do the receipts establish about run R-1042?"
    )
    report = verify_bundle(json.loads(bundle_bytes(meta)))
    assert report.verdict == "PASS"
    assert [u.verdict for u in report.upstreams] == ["PASS"]


def test_chain_answer_refusal_is_first_class(brief: dict[str, object]) -> None:
    """A question with no lexical overlap refuses — and the refusal chain
    bundle still verifies PASS (a refusal is a provable outcome)."""
    bundle = build_chain_bundle([_load(HONEST)], "zebra quasar xylophone")
    result = bundle["result"]
    assert isinstance(result, dict) and result["refused"] is True
    assert verify_bundle(json.loads(bundle_bytes(bundle))).verdict == "PASS"


# --- emission guards --------------------------------------------------------------


def test_forged_upstream_refuses_to_chain() -> None:
    """Cite only what re-verifies: the challenge's forged bundle cannot be
    chained — emission fails with the named reason, never a quiet downgrade."""
    with pytest.raises(ChainError, match="cite only what re-verifies"):
        build_chain_bundle([_load(FORGED)], "What do the receipts establish?")


def test_refusal_only_upstreams_are_not_citable() -> None:
    """A refusal has no claims to cite; chaining only refusals refuses."""
    refusal = json.loads(
        bundle_bytes(
            build_bundle(
                "business", "Which customer has the highest total order value?"
            )
        )
    )
    result = refusal["result"]
    assert isinstance(result, dict) and result["refused"] is True  # sanity
    with pytest.raises(ChainError, match="nothing citable"):
        build_chain_bundle([refusal], "totals?")


def test_duplicate_upstream_rejected() -> None:
    honest = _load(HONEST)
    with pytest.raises(ChainError, match="embedded twice"):
        build_chain_bundle([honest, copy.deepcopy(honest)], "totals?")


# --- the adversarial battery ------------------------------------------------------


def test_deep_forge_is_caught_by_recursion_alone(brief: dict[str, object]) -> None:
    """THE theorem test. The strongest attacker swaps the embedded honest
    bundle for the challenge's forgery (internally consistent, re-sealed) and
    rewrites EVERY chain-level reference to match — roots, record ids, and
    all claim/record texts — then re-seals the chain. The chain is now fully
    self-consistent: its answer re-derives, every chain claim matches, every
    record byte-matches the (forged) upstream claim. The ONLY thing left
    standing is the recursive upstream re-execution — and it catches the lie.
    """
    honest, forged = _load(HONEST), _load(FORGED)
    old_root, new_root = _root(honest), _root(forged)

    working = copy.deepcopy(brief)
    closure = working["evidence_closure"]
    assert isinstance(closure, dict)
    upstream_list = closure["upstream"]
    assert isinstance(upstream_list, list)
    closure["upstream"] = [
        forged if isinstance(u, dict) and _root(u) == old_root else u
        for u in upstream_list
    ]

    text = json.dumps({k: v for k, v in working.items() if k != "integrity"})
    text = text.replace(old_root, new_root)
    old12 = old_root.removeprefix("sha256:")[:12]
    new12 = new_root.removeprefix("sha256:")[:12]
    text = text.replace(f"chain:{old12}:", f"chain:{new12}:")
    honest_claims = honest["result"]["claims"]  # type: ignore[index]
    forged_claims = forged["result"]["claims"]  # type: ignore[index]
    for h, f in zip(honest_claims, forged_claims, strict=True):
        if h["text"] != f["text"]:
            text = text.replace(
                json.dumps(h["text"])[1:-1], json.dumps(f["text"])[1:-1]
            )
    forged_chain = seal(json.loads(text))

    report = verify_bundle(forged_chain)
    # Fully consistent inside...
    assert not report.integrity_problems
    assert report.answer_rederives is True
    assert all(c.matches for c in report.claims)
    # ...and still FAILED — by the recursive re-execution, nothing else.
    assert report.verdict == "FAIL" and report.exit_code == 2
    forged_check = next(u for u in report.upstreams if u.root == new_root)
    assert forged_check.verdict == "FAIL"
    assert any("does not re-verify (FAIL)" in p for p in report.semantic_problems)


def test_cited_text_tamper_is_caught_even_when_internally_consistent(
    brief: dict[str, object],
) -> None:
    """Alter one derived record's text everywhere it appears at the chain
    level (kb, graph node, result claim + support copies), re-seal. The
    upstreams are intact and PASS; the chain's own state is consistent enough
    to re-derive — the record↔upstream byte-match is what names the lie."""
    result = brief["result"]
    assert isinstance(result, dict)
    claims = result["claims"]
    assert isinstance(claims, list) and claims
    first = claims[0]
    assert isinstance(first, dict)
    original = first["text"]
    assert isinstance(original, str)
    tampered_text = original.replace("EUR", "EUR fully-audited", 1)
    assert tampered_text != original

    # Surgical: replace the text at the CHAIN level only — the embedded
    # upstreams (which also carry this text) must stay byte-intact.
    working = copy.deepcopy(brief)
    closure = working["evidence_closure"]
    assert isinstance(closure, dict)
    saved_upstreams = closure["upstream"]
    closure["upstream"] = []
    text = json.dumps({k: v for k, v in working.items() if k != "integrity"})
    escaped = json.dumps(original)[1:-1]
    assert text.count(escaped) >= 2  # kb record + graph node + result copies
    rebuilt = json.loads(text.replace(escaped, json.dumps(tampered_text)[1:-1]))
    rebuilt_closure = rebuilt["evidence_closure"]
    assert isinstance(rebuilt_closure, dict)
    rebuilt_closure["upstream"] = saved_upstreams
    tampered_chain = seal(rebuilt)

    report = verify_bundle(tampered_chain)
    assert not report.integrity_problems
    assert all(u.verdict == "PASS" for u in report.upstreams)  # upstreams intact
    assert report.verdict == "FAIL"
    assert any("does not match upstream claim" in p for p in report.semantic_problems)


def test_upstream_swap_is_caught(brief: dict[str, object]) -> None:
    """Replace an embedded upstream with a DIFFERENT passing bundle (re-seal
    the chain): the derived records cite a root that is no longer embedded."""
    other = json.loads(
        bundle_bytes(build_bundle("github_actions", "Why did the Pages deploy fail?"))
    )
    working = copy.deepcopy(brief)
    closure = working["evidence_closure"]
    assert isinstance(closure, dict)
    upstream_list = closure["upstream"]
    assert isinstance(upstream_list, list)
    honest_root = _root(_load(HONEST))
    closure["upstream"] = [
        other if isinstance(u, dict) and _root(u) == honest_root else u
        for u in upstream_list
    ]
    report = verify_bundle(_reseal(working))
    assert report.verdict == "FAIL"
    assert any("not embedded-and-passing" in p for p in report.semantic_problems)


def test_removed_upstream_is_caught(brief: dict[str, object]) -> None:
    working = copy.deepcopy(brief)
    closure = working["evidence_closure"]
    assert isinstance(closure, dict)
    upstream_list = closure["upstream"]
    assert isinstance(upstream_list, list)
    closure["upstream"] = upstream_list[:1]
    report = verify_bundle(_reseal(working))
    assert report.verdict == "FAIL"
    assert any("not embedded-and-passing" in p for p in report.semantic_problems)


def test_byte_flip_inside_embedded_upstream_breaks_the_envelope(
    brief: dict[str, object],
) -> None:
    """Tampering INSIDE an embedded upstream without re-sealing the chain is
    an integrity break: the `upstream:<root>` leaf no longer matches."""
    working = copy.deepcopy(brief)
    closure = working["evidence_closure"]
    assert isinstance(closure, dict)
    upstream_list = closure["upstream"]
    assert isinstance(upstream_list, list)
    victim = upstream_list[0]
    assert isinstance(victim, dict)
    victim_result = victim["result"]
    assert isinstance(victim_result, dict)
    victim_result["question"] = "a different question"
    report = verify_bundle(working)
    assert report.exit_code == 4
    assert any("upstream:" in p for p in report.integrity_problems)


def test_full_snapshot_bundle_cannot_smuggle_an_upstream_key() -> None:
    """A non-chain bundle carrying an `upstream` closure key is rejected at
    the envelope (the section set commits per kind)."""
    bundle = json.loads(bundle_bytes(build_bundle("devex", RCA_QUESTION)))
    closure = bundle["evidence_closure"]
    assert isinstance(closure, dict)
    closure["upstream"] = []
    report = verify_bundle(_reseal(bundle))
    assert report.exit_code == 4
    assert any(
        "unexpected evidence_closure key" in p for p in report.integrity_problems
    )


# --- the grammar ------------------------------------------------------------------


def test_chain_citation_grammar_owns_only_bundle_claims(
    brief: dict[str, object],
) -> None:
    """The citation grammar answers for bundle-claim-supported claims and
    stays silent (None) otherwise, so it can never hijack another vertical's
    claims."""
    from tessera.bundle.serde import graph_from_dict, kb_from_dict

    closure = brief["evidence_closure"]
    assert isinstance(closure, dict)
    graph_section = closure["graph"]
    kb_section = closure["kb"]
    assert isinstance(graph_section, dict) and isinstance(kb_section, dict)
    graph = graph_from_dict(graph_section)
    kb = kb_from_dict(kb_section)
    nodes = {node.id: node for node in graph.nodes}
    from tessera.grounding import Claim

    record = kb.records[0]
    assert (
        chain_citation(Claim(text=record.text, support=(record,)), nodes, graph) is True
    )
    # A text that diverges from the corpus record is owned and rejected.
    assert (
        chain_citation(
            Claim(text=record.text + " (edited)", support=(record,)), nodes, graph
        )
        is False
    )
    # A claim citing a non-bundle record is not this grammar's business.
    ordinary = json.loads(bundle_bytes(build_bundle("devex", RCA_QUESTION)))
    dev_closure = ordinary["evidence_closure"]
    assert isinstance(dev_closure, dict)
    dev_kb_section = dev_closure["kb"]
    assert isinstance(dev_kb_section, dict)
    dev_kb = kb_from_dict(dev_kb_section)
    dev_record = dev_kb.records[0]
    assert (
        chain_citation(Claim(text=dev_record.text, support=(dev_record,)), nodes, graph)
        is None
    )
    assert len(CHAIN_CLAIM_SHAPES) == 1


# --- CLI + surfaces ---------------------------------------------------------------


def test_cli_chain_and_front_door(tmp_path: Path) -> None:
    rca_path = tmp_path / "rca.tsb"
    rca_path.write_bytes(bundle_bytes(build_bundle("devex", RCA_QUESTION)))

    out = tmp_path / "brief.tsb"
    assert chain_main([CHAIN_QUESTION, str(rca_path), str(HONEST), "-o", str(out)]) == 0
    assert verify_bundle(_load(out)).verdict == "PASS"

    from tessera.cli import main as front_door

    out2 = tmp_path / "brief2.tsb"
    assert (
        front_door(["bundle", "chain", CHAIN_QUESTION, str(rca_path), "-o", str(out2)])
        == 0
    )


def test_cli_refuses_forged_upstream(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "x.tsb"
    code = chain_main(["totals?", str(FORGED), "-o", str(out)])
    assert code == 2
    assert "cite only what re-verifies" in capsys.readouterr().err
    assert not out.exists()


def test_explain_and_audit_render_chain_bundles(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from tessera.bundle.audit import audit_record, render_text
    from tessera.bundle.cli import explain_main

    record = audit_record(_load(BRIEF))
    assert record.verdict == "PASS" and record.domain == "chain"
    assert "re-derive" in render_text(record)

    assert explain_main([str(BRIEF)]) == 0
    assert "chain" in capsys.readouterr().out.lower()


# --- determinism + hygiene --------------------------------------------------------


def test_chain_bytes_stable_across_hash_seeds() -> None:
    """Chain emission is byte-identical across interpreter hash seeds (the
    spec-0133 property, held by the chain path too)."""
    script = (
        "import json, hashlib\n"
        "from tessera.bundle.chain import build_chain_bundle\n"
        "from tessera.bundle.emit import build_bundle, bundle_bytes\n"
        "rca = json.loads(bundle_bytes(build_bundle('devex', "
        f"{RCA_QUESTION!r})))\n"
        f"totals = json.loads(open({str(HONEST)!r}, encoding='utf-8').read())\n"
        f"data = bundle_bytes(build_chain_bundle([rca, totals], {CHAIN_QUESTION!r}))\n"
        "print(hashlib.sha256(data).hexdigest())\n"
    )
    digests = set()
    for seed in ("0", "1", "42"):
        # Copy the real environment and vary only PYTHONHASHSEED — a bare env
        # breaks subprocess launching on Windows (needs SystemRoot etc.).
        env = {**os.environ, "PYTHONHASHSEED": seed}
        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=True,
            env=env,
        )
        digests.add(proc.stdout.strip())
    assert len(digests) == 1


def test_chain_path_is_stdlib_only() -> None:
    """The chain surface must not pull an optional extra (the leak-guard)."""
    script = (
        "import sys\n"
        "import tessera.bundle.chain\n"
        "forbidden = {'mcp', 'hdbcli', 'pyarrow', 'nacl', 'numpy'}\n"
        "loaded = forbidden & set(sys.modules)\n"
        "assert not loaded, f'chain pulled {loaded}'\n"
    )
    subprocess.run([sys.executable, "-c", script], check=True)
