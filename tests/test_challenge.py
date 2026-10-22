"""The forged-bundle challenge is real and honest (spec 0140).

Pinned: the committed honest bundle verifies PASS and the forged one FAILs
naming the broken claim; the foil (integrity-only) reports BOTH intact — so
integrity checking genuinely cannot tell them apart; the forged bundle's
cited evidence is untouched (the lie is in the conclusion); and both
committed files are byte-identical to a fresh forge run (the forgery cannot
drift from its script). No SALT-derived values anywhere.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tessera.bundle.emit import bundle_bytes
from tessera.bundle.format import integrity_mismatches
from tessera.bundle.verify import verify_bundle

REPO = Path(__file__).resolve().parents[1]
HONEST = REPO / "data" / "challenge" / "honest.tsb"
FORGED = REPO / "data" / "challenge" / "forged.tsb"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def test_committed_bundles_exist() -> None:
    assert HONEST.is_file() and FORGED.is_file()


def test_honest_passes_forged_fails() -> None:
    honest = verify_bundle(_load(HONEST))
    assert honest.verdict == "PASS" and honest.exit_code == 0

    forged = verify_bundle(_load(FORGED))
    assert forged.verdict == "FAIL" and forged.exit_code == 2
    # The break is named, and it is the inflated total.
    unsupported = [c for c in forged.claims if not c.rederived]
    assert unsupported, "the forged bundle must fail at least one claim"
    assert any("88,000" in c.text for c in unsupported)


def test_integrity_cannot_tell_them_apart() -> None:
    """The honest core of the challenge: signature/hash-chain-style checking
    passes BOTH — only re-execution separates them."""
    assert integrity_mismatches(_load(HONEST)) == []
    assert integrity_mismatches(_load(FORGED)) == []


def test_forged_evidence_is_untouched() -> None:
    """The lie is in the conclusion, not the records — the forged bundle's
    graph (its evidence) is byte-identical to the honest one; only the claim
    texts differ."""
    honest, forged = _load(HONEST), _load(FORGED)
    assert honest["evidence_closure"] == forged["evidence_closure"]
    honest_claims = honest["result"]["claims"]  # type: ignore[index]
    forged_claims = forged["result"]["claims"]  # type: ignore[index]
    # Same support, different claim text (the inflation).
    assert [c["support"] for c in honest_claims] == [
        c["support"] for c in forged_claims
    ]
    assert [c["text"] for c in honest_claims] != [c["text"] for c in forged_claims]


def _load_forge_module() -> object:
    """Load the forge script by path (scripts/ is not an importable package)."""
    import importlib.util

    path = REPO / "scripts" / "forge_challenge_bundle.py"
    spec = importlib.util.spec_from_file_location("forge_challenge_bundle", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_committed_bundles_match_a_fresh_forge_run() -> None:
    """The forgery cannot drift from the script that explains it: the committed
    files must be byte-identical to a fresh, deterministic build."""
    forge = _load_forge_module()
    honest = forge.build_honest()  # type: ignore[attr-defined]
    forged = forge.forge(honest)  # type: ignore[attr-defined]
    assert bundle_bytes(honest) == HONEST.read_bytes()
    assert bundle_bytes(forged) == FORGED.read_bytes()


def test_no_salt_values_in_the_challenge() -> None:
    """The challenge is synthetic-only — a downloadable bundle never carries
    gated SALT-derived data. The synthetic corpus tags its source path."""
    for path in (HONEST, FORGED):
        text = path.read_text(encoding="utf-8")
        assert "salt_synthetic" in text  # the synthetic corpus
        assert "salt_real" not in text and "var/salt_real" not in text


def test_llm_judge_contrast_runs_without_a_key() -> None:
    """The LLM-judge one-shot is manual, never CI: with no key it prints
    guidance and exits 0 (never a hard dependency, never a failure)."""
    proc = subprocess.run(
        [sys.executable, str(REPO / "scripts" / "llm_judge_contrast.py")],
        capture_output=True,
        text=True,
        env={"PATH": __import__("os").environ.get("PATH", "")},  # no ANTHROPIC_API_KEY
        cwd=REPO,
    )
    assert proc.returncode == 0
    assert "no ANTHROPIC_API_KEY" in proc.stdout
