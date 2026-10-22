"""Tests for `tessera bundle audit` — the decision record (spec 0139).

The load-bearing risk of this feature is overclaiming, so the tests pin the
honesty guardrails: the record faithfully reflects the verify verdict (the
forged bundle records FAILED — never a rubber stamp), a broken envelope
cannot be audited, and every record carries the disclaimer with the
*corrected* (deferred to Dec 2027) timeline so a stale or overclaiming edit
fails the build.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tessera.bundle.audit import DISCLAIMER, audit_record, render_text
from tessera.bundle.cli import audit_main
from tessera.bundle.emit import build_action_bundle, build_bundle, bundle_bytes
from tessera.bundle.verify import BundleFormatError

REPO = Path(__file__).resolve().parents[1]
HONEST = REPO / "data" / "challenge" / "honest.tsb"
FORGED = REPO / "data" / "challenge" / "forged.tsb"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_honest_bundle_records_pass_and_the_mapping() -> None:
    record = audit_record(_load(HONEST))
    assert record.verdict == "PASS"
    assert record.re_derivable and not record.refused
    assert record.verified_claim_count == record.claim_count == 3
    articles = {row.article for row in record.mapping}
    assert "Art. 12" in articles and "Art. 14" in articles


def test_forged_bundle_records_failed_never_a_rubber_stamp() -> None:
    """The whole honesty point: an audit record of a failing decision says so —
    and its claim count comes from the RE-EXECUTION, never from the bundle's
    own recorded flags (the forger controls those; all 3 read verified=true)."""
    record = audit_record(_load(FORGED))
    assert record.verdict == "FAIL"
    assert record.claim_count == 3
    # The inflated total fails AND the comparison conclusion built on it fails:
    # only the untouched claim re-derives. (Recorded flags would say 3/3.)
    assert record.verified_claim_count == 1
    text = render_text(record)
    assert "FAILED re-verification" in text
    assert "do NOT re-derive" in text
    assert "1/3 claim(s) re-derive" in text


def test_action_bundle_records_human_oversight() -> None:
    bundle = build_action_bundle(
        "incident", "devex", "Why did run R-1042 fail, and has this happened before?"
    )
    record = audit_record(json.loads(bundle_bytes(bundle)))
    assert record.has_action
    oversight = next(r for r in record.mapping if r.article == "Art. 14")
    assert oversight.carried
    assert "requires_approval=True" in oversight.detail
    assert "approved=False" in oversight.detail


def test_answer_only_bundle_marks_oversight_not_carried() -> None:
    record = audit_record(build_bundle("business", "Compare Acme and Beta totals."))
    oversight = next(r for r in record.mapping if r.article == "Art. 14")
    # Honest: an answer-only bundle has no approval gate, and the row says so.
    assert not oversight.carried
    assert "answer only" in oversight.detail


def test_degraded_bundle_records_not_re_derivable() -> None:
    """The third reachable verdict: a bundle this engine cannot re-derive
    (engine-pin mismatch, re-sealed) must not read as re-verified — the record
    says DEGRADED and the Art. 12 purpose row says the re-execution did not
    happen here. (TAMPERED is unreachable by construction: its condition is
    exactly the envelope refusal pinned above.)"""
    from tessera.bundle.mutations import engine_version_spoof

    record = audit_record(engine_version_spoof(_load(HONEST)).bundle)
    assert record.verdict == "DEGRADED"
    assert not record.re_derivable
    assert record.verified_claim_count is None  # no re-execution → no count
    why = next(r for r in record.mapping if r.article == "Art. 12 (purpose)")
    assert not why.carried
    assert "cannot re-derive" in why.detail
    text = render_text(record)
    assert "not re-executed to a pass" in text
    assert "not re-executed here" in text


def test_broken_envelope_cannot_be_audited() -> None:
    bundle = _load(HONEST)
    integrity = bundle["integrity"]
    assert isinstance(integrity, dict)
    integrity["root"] = "sha256:" + "0" * 64
    with pytest.raises(BundleFormatError, match="cannot produce an audit record"):
        audit_record(bundle)


def test_disclaimer_is_honest_and_correctly_dated() -> None:
    """Pinned so a stale/overclaiming edit fails: no 'compliant' claim, the
    deferred Dec-2027 date, and the drafts caveat are all present."""
    text = render_text(audit_record(_load(HONEST)))
    assert DISCLAIMER in text
    assert "not a compliance attestation" in DISCLAIMER
    assert "legal advice" in DISCLAIMER
    assert "2 December 2027" in DISCLAIMER  # the corrected (deferred) date
    assert "drafts" in DISCLAIMER
    # The verb never asserts conformance.
    lowered = text.lower()
    assert "certified" not in lowered
    assert "regulator-ready" not in lowered
    assert "is compliant" not in lowered


def test_cli_audit_pass_json_and_broken(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "a.tsb"
    out.write_bytes(bundle_bytes(build_bundle("business", "Compare Acme and Beta.")))
    assert audit_main([str(out)]) == 0
    assert "audit record" in capsys.readouterr().out.lower()

    assert audit_main([str(out), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["eu_ai_act_mapping"] and "disclaimer" in payload

    broken = tmp_path / "broken.tsb"
    tampered = json.loads(out.read_text())
    tampered["integrity"]["root"] = "sha256:" + "0" * 64
    broken.write_text(json.dumps(tampered))
    assert audit_main([str(broken)]) == 4
    assert "cannot produce" in capsys.readouterr().err


def test_front_door_dispatches_audit(tmp_path: Path) -> None:
    from tessera.cli import main as front_door

    out = tmp_path / "fd.tsb"
    out.write_bytes(bundle_bytes(build_bundle("devex", "Why did run R-1042 fail?")))
    assert front_door(["bundle", "audit", str(out)]) == 0


def test_audit_path_is_stdlib_only() -> None:
    """The audit surface must not pull an optional extra (the leak-guard)."""
    import subprocess
    import sys

    script = (
        "import sys\n"
        "import tessera.bundle.audit\n"
        "forbidden = {'mcp', 'hdbcli', 'pyarrow', 'nacl', 'numpy'}\n"
        "loaded = forbidden & set(sys.modules)\n"
        "assert not loaded, f'audit pulled {loaded}'\n"
    )
    subprocess.run([sys.executable, "-c", script], check=True)
