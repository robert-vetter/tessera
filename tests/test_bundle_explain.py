"""Tests for `tessera bundle explain` (spec 0142).

Pinned: the chain renders (question, claims + verdicts, cited evidence,
action + provenance); the verdict shown equals verify's, so a tampered
bundle is shown as failing (explain never launders a bad bundle); --json
round-trips; a bare question is not mistaken for the explain subcommand.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tessera.bundle.cli import explain_main
from tessera.bundle.cli import main as bundle_cli
from tessera.bundle.emit import build_action_bundle, build_bundle, bundle_bytes
from tessera.bundle.explain import explain_bundle, render_text
from tessera.bundle.format import seal

_Q = "Compare Müller Logistik and Nordwind Logistik totals."


def _reseal(bundle: dict[str, object]) -> dict[str, object]:
    return seal({k: v for k, v in bundle.items() if k != "integrity"})


def test_explains_a_grounded_answer() -> None:
    exp = explain_bundle(build_bundle("business", _Q))
    assert exp.verdict == "PASS"
    assert exp.question == _Q
    assert len(exp.claims) == 3
    assert all(c.status == "re-derived" for c in exp.claims)
    assert all(c.evidence for c in exp.claims)  # every claim cites evidence
    assert exp.cited_records > 0 and exp.packaged_records >= exp.cited_records
    text = render_text(exp, source="x.tsb")
    assert "verdict:  PASS" in text and "re-derived]" in text
    assert "salt_synthetic" in text  # provenance is shown


def test_explains_a_refusal() -> None:
    exp = explain_bundle(build_bundle("devex", "What is the meaning of life?"))
    assert exp.refused and exp.refusal
    assert exp.claims == ()
    assert "refusal:" in render_text(exp, source="x.tsb")


def test_explains_an_action_bundle() -> None:
    exp = explain_bundle(
        build_action_bundle("incident", "devex", "Why did run R-1042 fail?")
    )
    assert exp.action is not None
    assert exp.action.method == "POST" and exp.action.simulated
    assert exp.action.slots and all(s.provenance for s in exp.action.slots)
    assert "action:" in render_text(exp, source="x.tsb")


def test_a_tampered_bundle_is_shown_as_failing() -> None:
    """The honesty property: explain shows verify's verdict, so a re-sealed
    tamper is rendered FAIL with the broken claim UNSUPPORTED — never dressed
    as sound."""
    bundle: Any = build_bundle("business", _Q)
    cited = bundle["result"]["claims"][0]["support"][0]["id"]
    for node in bundle["evidence_closure"]["graph"]["nodes"]:
        if node["record"]["id"] == cited:
            old = dict(node["attributes"])["net_amount"]
            new = str(int(float(old)) + 50000) + ".00"
            node["attributes"] = [
                [k, new if k == "net_amount" else v] for k, v in node["attributes"]
            ]
            node["record"]["text"] = str(node["record"]["text"]).replace(old, new)
            break
    exp = explain_bundle(_reseal(bundle))
    assert exp.verdict == "FAIL"
    assert any(c.status == "UNSUPPORTED" for c in exp.claims)
    assert "FAIL" in render_text(exp, source="x.tsb")


def test_degraded_bundle_shows_recorded_status() -> None:
    """A NOT-EVALUABLE bundle is not re-executed; its claims are shown as
    'recorded', and the header carries the degraded verdict + reason."""
    bundle: Any = build_bundle("business", _Q)
    bundle["engine"]["tessera_version"] = "9.9.9"
    exp = explain_bundle(_reseal(bundle))
    assert exp.verdict == "DEGRADED"
    assert all(c.status == "recorded" for c in exp.claims)
    assert "9.9.9" in render_text(exp, source="x.tsb")


def test_truncation_and_full() -> None:
    bundle = build_bundle("business", _Q)
    short = explain_bundle(bundle, full=False)
    full = explain_bundle(bundle, full=True)
    short_snips = [e.snippet for c in short.claims for e in c.evidence]
    full_snips = [e.snippet for c in full.claims for e in c.evidence]
    # Same evidence, but full is never elided.
    assert any("…" in s for s in short_snips) or all(len(s) <= 100 for s in short_snips)
    assert not any("(+" in s and "chars)" in s for s in full_snips)


def test_json_round_trips(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "a.tsb"
    out.write_bytes(bundle_bytes(build_bundle("business", _Q)))
    assert explain_main([str(out), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["verdict"] == "PASS"
    assert len(payload["claims"]) == 3
    assert payload["claims"][0]["evidence"][0]["source"].startswith("salt_synthetic")


def test_cli_text_and_missing_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "a.tsb"
    out.write_bytes(
        bundle_bytes(
            build_action_bundle("incident", "devex", "Why did run R-1042 fail?")
        )
    )
    assert explain_main([str(out)]) == 0
    assert "action:" in capsys.readouterr().out
    assert explain_main([str(tmp_path / "nope.tsb")]) == 4


def test_bare_question_is_not_mistaken_for_explain(tmp_path: Path) -> None:
    """`tessera bundle explain <file>` dispatches to explain; a real question
    (a quoted string) is one argv token and never matches the verb."""
    out = tmp_path / "q.tsb"
    # A question that literally starts with the word "explain" stays one token.
    code = bundle_cli(
        [
            "explain the Müller vs Nordwind totals",
            "--domain",
            "business",
            "-o",
            str(out),
        ]
    )
    assert code == 0 and out.exists()  # emitted, not treated as the explain verb


def test_explain_via_front_door(tmp_path: Path) -> None:
    from tessera.cli import main as front_door

    out = tmp_path / "fd.tsb"
    out.write_bytes(
        bundle_bytes(build_bundle("github_actions", "Why did the pages deploy fail?"))
    )
    assert front_door(["bundle", "explain", str(out)]) == 0
