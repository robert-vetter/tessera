"""Tests for the offline re-executing verifier (spec 0134).

The trust-bearing surface of Milestone 20: intact bundles pass in every
committed domain; the milestone floor (100% re-derivation equality across
every gold case of all three batteries) holds; each attack class lands in
the right layer with the right exit code and a named cause — including the
re-sealed tamper the integrity layer cannot see and the claim-swap that
only answer re-derivation catches.
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

from tessera.bundle.cli import verify_main
from tessera.bundle.emit import build_bundle, bundle_bytes
from tessera.bundle.format import seal
from tessera.bundle.verify import (
    INTEGRITY_ONLY,
    NOT_EVALUABLE,
    RE_DERIVED,
    BundleFormatError,
    ClaimCheck,
    VerifyReport,
    verify_bundle,
)
from tessera.eval.harness import load_gold_set
from tessera.eval.registry import batteries

_DOMAINS = ("business", "devex", "github_actions")
_GROUNDED = {
    "business": "Compare Müller Logistik and Nordwind Logistik totals.",
    "devex": "Why did run R-1042 fail, and has this happened before?",
    "github_actions": "Why did the pages deploy fail?",
}
_REFUSED = "What is the meaning of life?"


def _fresh(name: str, question: str) -> dict[str, object]:
    """A bundle as verify sees it: through the file-byte round trip."""
    return json.loads(bundle_bytes(build_bundle(name, question)))  # type: ignore[no-any-return]


def _reseal(bundle: dict[str, object]) -> dict[str, object]:
    """What a tamperer does after editing content: recompute manifest + root
    (trivial until signatures land in unit 0135)."""
    stripped = {k: v for k, v in bundle.items() if k != "integrity"}
    return seal(stripped)


def _graph_nodes(bundle: dict[str, object]) -> list[dict[str, object]]:
    closure = bundle["evidence_closure"]
    assert isinstance(closure, dict)
    graph = closure["graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    return nodes


def _result(bundle: dict[str, object]) -> dict[str, object]:
    result = bundle["result"]
    assert isinstance(result, dict)
    return result


def _tamper_cited_amount(bundle: dict[str, object]) -> dict[str, object]:
    """Flip one digit of a row the first claim actually cites, in both the
    graph node and its record text, then re-seal."""
    tampered = copy.deepcopy(bundle)
    claims = _result(tampered)["claims"]
    assert isinstance(claims, list) and claims
    first = claims[0]
    assert isinstance(first, dict)
    support = first["support"]
    assert isinstance(support, list) and support
    cited = support[0]
    assert isinstance(cited, dict)
    cited_id = cited["id"]
    for node in _graph_nodes(tampered):
        record = node["record"]
        assert isinstance(record, dict)
        if record["id"] == cited_id:
            attributes = node["attributes"]
            assert isinstance(attributes, list)
            old = dict((k, v) for k, v in attributes)["net_amount"]  # noqa: C402
            assert isinstance(old, str)
            new = str(int(float(old)) + 30000) + ".00"
            node["attributes"] = [
                [k, (new if k == "net_amount" else v)] for k, v in attributes
            ]
            record["text"] = str(record["text"]).replace(old, new)
            return _reseal(tampered)
    raise AssertionError(f"cited record {cited_id!r} not found in the snapshot")


# --- intact bundles -----------------------------------------------------------------


@pytest.mark.parametrize("name", _DOMAINS)
def test_intact_grounded_bundle_passes(name: str) -> None:
    report = verify_bundle(_fresh(name, _GROUNDED[name]))
    assert report.taxonomy == RE_DERIVED
    assert report.integrity_problems == ()
    assert report.semantic_problems == ()
    assert report.answer_rederives is True
    assert all(c.matches and c.rederived for c in report.claims)
    assert report.exit_code == 0 and report.verdict == "PASS"


@pytest.mark.parametrize("name", _DOMAINS)
def test_intact_refusal_bundle_passes(name: str) -> None:
    report = verify_bundle(_fresh(name, _REFUSED))
    assert report.refused and report.claims == ()
    assert report.answer_rederives is True
    assert report.exit_code == 0


def test_milestone_floor_every_gold_case_rederives() -> None:
    """The Milestone-20 floor (spec 0131): for EVERY gold case of all three
    committed batteries, emit → verify from the file bytes alone yields
    100% re-derivation equality — integrity intact, every recorded claim
    verdict re-derived and matching, the answer re-deriving. (The standing
    CI artifact with its own doc is unit 0137; this pins the property.)"""
    total = 0
    for battery in batteries():
        for case in load_gold_set(battery.gold_dir):
            report = verify_bundle(_fresh(battery.name, case.question))
            assert report.taxonomy == RE_DERIVED, (battery.name, case.id)
            assert report.integrity_problems == (), (battery.name, case.id)
            assert report.semantic_problems == (), (battery.name, case.id)
            assert report.answer_rederives is True, (battery.name, case.id)
            total += 1
    assert total >= 25  # all three gold sets, none silently skipped


# --- the attack classes ---------------------------------------------------------------


def test_flip_a_byte_reseal_names_the_dependent_claims() -> None:
    """THE demo (spec 0131): tamper a cited amount, re-seal. Integrity is
    intact — what a signature-style verifier sees — while re-execution fails
    exactly the dependent claims, with named causes, exit 2."""
    tampered = _tamper_cited_amount(_fresh("business", _GROUNDED["business"]))
    report = verify_bundle(tampered)
    assert report.integrity_problems == ()  # the foil's whole world is green
    failed = [c for c in report.claims if not c.matches]
    assert failed, "the dependent claim must fail"
    assert all(c.recorded and not c.rederived for c in failed)
    assert all(c.cause and "does not re-derive" in c.cause for c in failed)
    # The untouched claim still re-derives — failure is localized, not global.
    assert any(c.matches and c.rederived for c in report.claims)
    assert report.answer_rederives is False
    assert report.exit_code == 2 and report.verdict == "FAIL"


def test_tamper_without_reseal_breaks_the_envelope_and_still_reports() -> None:
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    nodes = _graph_nodes(tampered)
    record = nodes[0]["record"]
    assert isinstance(record, dict)
    record["text"] = str(record["text"]) + " [tampered]"
    report = verify_bundle(tampered)
    assert any("leaf" in p for p in report.integrity_problems)
    assert report.exit_code == 4 and report.verdict == "TAMPERED"
    assert report.claims  # the semantic layer still ran and is reported


def test_claim_swap_is_caught_by_answer_rederivation_alone() -> None:
    """Replace the claims with DIFFERENT, individually true, re-derivable
    claims from the same corpus and re-seal: check (a) passes every claim —
    which is exactly why check (b) exists — and (b) catches the swap."""
    target = _fresh("business", _GROUNDED["business"])
    donor = _fresh("business", "What is the total net order value for Müller Logistik?")
    donor_claims = _result(donor)["claims"]
    assert isinstance(donor_claims, list) and donor_claims
    swapped = copy.deepcopy(target)
    result = _result(swapped)
    result["claims"] = copy.deepcopy(donor_claims)
    result["all_verified"] = True
    swapped = _reseal(swapped)

    report = verify_bundle(swapped)
    assert report.integrity_problems == ()
    assert all(c.matches for c in report.claims)  # (a) alone would pass this
    assert report.answer_rederives is False  # (b) is the catch
    assert report.answer_cause and "diverge" in report.answer_cause
    assert report.exit_code == 2


def test_question_swap_is_caught() -> None:
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    _result(tampered)["question"] = (
        "What is the total net order value for Müller Logistik?"
    )
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    assert report.answer_rederives is False
    assert report.exit_code == 2


def test_verdict_flip_is_caught_as_mismatch() -> None:
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    claims = _result(tampered)["claims"]
    assert isinstance(claims, list)
    first = claims[0]
    assert isinstance(first, dict)
    first["verified"] = False
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    flipped = report.claims[0]
    assert flipped.rederived and not flipped.recorded and not flipped.matches
    assert flipped.cause and "altered" in flipped.cause
    assert report.exit_code == 2


def test_refusal_reason_edit_is_caught() -> None:
    bundle = _fresh("devex", _REFUSED)
    tampered = copy.deepcopy(bundle)
    _result(tampered)["refusal"] = "a fabricated refusal reason"
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    assert report.answer_rederives is False
    assert report.answer_cause and "refusal reason" in report.answer_cause
    assert report.exit_code == 2


def test_structural_violation_is_a_semantic_failure() -> None:
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    result = _result(tampered)
    result["refused"] = True  # grounded AND refused: the impossible record
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    assert any("exactly-one-mode" in p for p in report.structural_problems)
    assert report.exit_code == 2


# --- visible degradation, never a false PASS ------------------------------------------


def test_version_spoof_degrades_to_not_evaluable() -> None:
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    engine = tampered["engine"]
    assert isinstance(engine, dict)
    engine["tessera_version"] = "9.9.9"
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    assert report.taxonomy == NOT_EVALUABLE
    assert report.taxonomy_reason and "9.9.9" in report.taxonomy_reason
    assert report.claims == () and report.answer_rederives is None
    assert report.exit_code == 3 and report.verdict == "DEGRADED"


def test_shape_identifier_spoof_degrades_to_not_evaluable() -> None:
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    engine = tampered["engine"]
    assert isinstance(engine, dict)
    engine["claim_shapes"] = ["somebody.elses.grammar"]
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    assert report.taxonomy == NOT_EVALUABLE
    assert report.exit_code == 3


def test_unknown_domain_degrades_to_not_evaluable() -> None:
    bundle = _fresh("devex", _GROUNDED["devex"])
    tampered = copy.deepcopy(bundle)
    engine = tampered["engine"]
    assert isinstance(engine, dict)
    engine["domain"] = "some_future_domain"
    result = _result(tampered)
    result["domain"] = "some_future_domain"
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    assert report.taxonomy == NOT_EVALUABLE
    assert report.taxonomy_reason and "some_future_domain" in report.taxonomy_reason
    assert report.exit_code == 3


def test_genuinely_partial_closure_degrades_to_integrity_only() -> None:
    """A closure with no re-derivable graph is honestly INTEGRITY-ONLY —
    decided on what is PRESENT (no nodes), not on the label."""
    bundle = _fresh("devex", _GROUNDED["devex"])
    tampered = copy.deepcopy(bundle)
    closure = tampered["evidence_closure"]
    assert isinstance(closure, dict)
    closure["kind"] = "cited-records-only"
    graph = closure["graph"]
    assert isinstance(graph, dict)
    graph["nodes"] = []  # genuinely nothing to re-execute against
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    assert report.taxonomy == INTEGRITY_ONLY
    assert report.taxonomy_reason and "cannot be re-executed" in report.taxonomy_reason
    assert report.exit_code == 3


def test_kind_downgrade_cannot_suppress_reexecution() -> None:
    """The downgrade attack (adversarial review, finding 1): tamper a cited
    amount + re-seal (a real semantic FAIL), then relabel the closure kind to
    a partial value to try to switch the semantic layer OFF. Because a full
    graph is packaged, re-execution runs anyway — the tampered claims fail AND
    the label inconsistency is flagged; exit 2, never a silent DEGRADED."""
    tampered = _tamper_cited_amount(_fresh("business", _GROUNDED["business"]))
    closure = tampered["evidence_closure"]
    assert isinstance(closure, dict)
    closure["kind"] = "cited-records-only"
    tampered = _reseal(tampered)  # re-seal so integrity stays intact
    report = verify_bundle(tampered)
    assert report.integrity_problems == ()  # the foil still sees green
    assert report.taxonomy == RE_DERIVED  # NOT downgraded to INTEGRITY-ONLY
    assert any(not c.matches for c in report.claims)  # the tampered claim fails
    assert any("cannot suppress re-execution" in p for p in report.structural_problems)
    assert report.exit_code == 2  # semantic FAIL, not a silent degrade


def test_fabricated_provenance_render_is_caught() -> None:
    """Adversarial review (finding 2): the human-readable provenance pointer
    (``locator.render``) is a derived field reconstruction drops — but check
    (b) compares canonical bytes, so a fabricated render fails, not passes."""
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    claims = _result(tampered)["claims"]
    assert isinstance(claims, list)
    for claim in claims:
        assert isinstance(claim, dict)
        support = claim["support"]
        assert isinstance(support, list)
        for evidence in support:
            assert isinstance(evidence, dict)
            locator = evidence["locator"]
            assert isinstance(locator, dict)
            locator["render"] = "table PAYROLL_SECRETS, row 7"
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    assert report.integrity_problems == ()
    assert report.answer_rederives is False
    assert report.answer_cause and "provenance" in report.answer_cause
    assert report.exit_code == 2


def test_fabricated_all_verified_summary_is_caught() -> None:
    """The ``all_verified`` derived summary is likewise bound by check (b)."""
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    result = _result(tampered)
    result["all_verified"] = False  # lie in the derived summary
    tampered = _reseal(tampered)
    report = verify_bundle(tampered)
    assert report.answer_rederives is False
    assert report.exit_code == 2


def test_deleted_cited_node_is_a_clean_exit_2_not_a_crash() -> None:
    """Adversarial review (workflow, finding A): deleting a cited node and
    re-sealing left a dangling reference that crashed re-execution with an
    uncaught KeyError (exit 1, outside the taxonomy). It is now a named
    semantic failure — a clean, visible non-PASS verdict."""
    bundle = _fresh("business", _GROUNDED["business"])
    cited_id = _result(bundle)["claims"][0]["support"][0]["id"]  # type: ignore[index]
    closure = bundle["evidence_closure"]
    assert isinstance(closure, dict)
    graph = closure["graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    graph["nodes"] = [
        n for n in nodes if not (isinstance(n, dict) and n["record"]["id"] == cited_id)
    ]
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)  # must not raise
    assert report.integrity_problems == ()
    assert any(cited_id in p for p in report.structural_problems)
    assert report.exit_code == 2 and report.verdict == "FAIL"


def test_ghost_edge_is_a_clean_exit_2_not_a_crash() -> None:
    """A ghost edge (src is a node id absent from the snapshot) is caught by
    the referential-integrity check instead of crashing the router path."""
    bundle = _fresh("business", _GROUNDED["business"])
    closure = bundle["evidence_closure"]
    assert isinstance(closure, dict)
    graph = closure["graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    real = nodes[0]
    assert isinstance(real, dict)
    edges = graph["edges"]
    assert isinstance(edges, list)
    edges.append(
        {"src": "GHOST_NODE", "dst": real["record"]["id"], "relation": "sold_to"}
    )
    tampered = _reseal(bundle)
    report = verify_bundle(tampered)
    assert any("GHOST_NODE" in p for p in report.structural_problems)
    assert report.exit_code == 2


def test_no_committed_bundle_crashes_verify() -> None:
    """The robustness floor: every gold-case bundle verifies to a defined
    verdict (0/2/3/4), never an exception — the 'run verify offline' promise."""
    for battery in batteries():
        for case in load_gold_set(battery.gold_dir):
            report = verify_bundle(_fresh(battery.name, case.question))
            assert report.exit_code in (0, 2, 3, 4)


def test_exit_precedence_envelope_beats_semantic() -> None:
    """Tampered content AND stale hashes: 4 wins over 2."""
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = _tamper_cited_amount(bundle)  # re-sealed, semantic FAIL
    integrity = tampered["integrity"]
    assert isinstance(integrity, dict)
    integrity["root"] = "sha256:" + "0" * 64  # now the envelope is broken too
    report = verify_bundle(tampered)
    assert report.semantic_problems and report.integrity_problems
    assert report.exit_code == 4


# --- taxonomy corners (function level) ----------------------------------------


def test_honestly_unverified_claim_is_a_match_and_degrades() -> None:
    """recorded=false that re-derives false is a faithful record of an
    unverified claim — a match, not a mismatch; visible as DEGRADED.
    (Unreachable on the committed corpora, whose faithfulness floor is 1.0.)"""
    check = ClaimCheck(
        index=0, text="unsupported text", recorded=False, rederived=False, cause=None
    )
    assert check.matches
    report = VerifyReport(
        domain="business",
        sealed_under="0.0.0",
        installed="0.0.0",
        taxonomy=RE_DERIVED,
        taxonomy_reason=None,
        integrity_problems=(),
        signature_status="UNSIGNED",
        signature_public_key=None,
        signature_problems=(),
        structural_problems=(),
        claims=(check,),
        answer_rederives=True,
        answer_cause=None,
        refused=False,
    )
    assert report.semantic_problems == ()
    assert report.degraded and report.exit_code == 3


def test_wrong_format_major_is_an_envelope_error() -> None:
    bundle = _fresh("devex", _REFUSED)
    tampered = copy.deepcopy(bundle)
    fmt = tampered["format"]
    assert isinstance(fmt, dict)
    fmt["major"] = 2
    with pytest.raises(BundleFormatError, match="format major"):
        verify_bundle(tampered)


def test_non_null_anchor_is_refused() -> None:
    """Adversarial audit (final review, finding 2): the reserved anchor section
    has no verifier yet, so a non-null anchor is unverifiable content this
    version must refuse rather than ignore — even re-sealed."""
    bundle = _fresh("business", _GROUNDED["business"])
    tampered = copy.deepcopy(bundle)
    tampered["anchor"] = {"forged": "rekor-entry"}
    with pytest.raises(BundleFormatError, match="anchor section is reserved"):
        verify_bundle(_reseal(tampered))


# --- the CLI ------------------------------------------------------------------------


def test_cli_verify_pass_and_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from tessera.bundle.cli import main as bundle_cli

    out = tmp_path / "a.tsb"
    assert bundle_cli([_GROUNDED["devex"], "--domain", "devex", "-o", str(out)]) == 0
    capsys.readouterr()

    assert verify_main([str(out)]) == 0
    human = capsys.readouterr().out
    assert "verdict:   PASS (exit 0)" in human

    assert verify_main([str(out), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "PASS" and payload["exit_code"] == 0


def test_cli_verify_tampered_file_exits_2(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tampered = _tamper_cited_amount(_fresh("business", _GROUNDED["business"]))
    path = tmp_path / "tampered.tsb"
    path.write_bytes(bundle_bytes(tampered))
    assert verify_main([str(path)]) == 2
    out = capsys.readouterr().out
    assert "integrity: intact" in out and "UNSUPPORTED" in out


def test_cli_verify_unreadable_inputs_exit_4(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert verify_main([str(tmp_path / "missing.tsb")]) == 4
    not_json = tmp_path / "not.tsb"
    not_json.write_text("not json at all", encoding="utf-8")
    assert verify_main([str(not_json)]) == 4
    array = tmp_path / "array.tsb"
    array.write_text("[1,2,3]", encoding="utf-8")
    assert verify_main([str(array)]) == 4
    capsys.readouterr()


def test_cli_verify_rejects_duplicate_keys(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A trust bundle must be single-valued: duplicate keys (which a
    first-wins streaming reader could interpret differently than the verifier)
    are refused at the file boundary (adversarial review, finding 4)."""
    doubled = tmp_path / "doubled.tsb"
    doubled.write_text('{"format": 1, "format": 2}', encoding="utf-8")
    assert verify_main([str(doubled)]) == 4
    assert "duplicate key" in capsys.readouterr().err


def test_front_door_dispatches_verify(tmp_path: Path) -> None:
    from tessera.cli import main as front_door

    out = tmp_path / "fd.tsb"
    assert (
        front_door(["bundle", _REFUSED, "--domain", "github_actions", "-o", str(out)])
        == 0
    )
    assert front_door(["verify", str(out)]) == 0


def test_verify_path_pulls_no_optional_extras() -> None:
    """The stdlib-only promise: importing the whole verify surface must not
    pull the optional extras (the leak-guard pattern, extended)."""
    script = (
        "import sys\n"
        "import tessera.bundle.cli\n"
        "import tessera.bundle.verify\n"
        "forbidden = {'mcp', 'hdbcli', 'pyarrow', 'numpy'}\n"
        "loaded = forbidden & set(sys.modules)\n"
        "assert not loaded, f'verify path pulled {loaded}'\n"
    )
    subprocess.run([sys.executable, "-c", script], check=True)
