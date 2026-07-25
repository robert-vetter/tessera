"""Tests for the browser verifier (spec 0150, ADR 0040).

Two properties carry this unit, and both are testable rather than
promised:

- **the page is the same verifier**, not a second implementation that will
  drift (it inlines the shared core, and the committed file is pinned
  byte-identical to a fresh build);
- **nothing leaves the device** — the generated page contains no network
  API and no cross-origin reference at all.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PAGE = REPO / "docs" / "verify.html"
CORE = REPO / "verifier" / "js" / "verify-core.mjs"

_HAVE_NODE = shutil.which("node") is not None
_needs_node = pytest.mark.skipif(not _HAVE_NODE, reason="needs Node (installed in CI)")


def _page() -> str:
    return PAGE.read_text(encoding="utf-8")


# --- the artifact -------------------------------------------------------------------


def test_page_is_committed_and_self_contained() -> None:
    page = _page()
    assert page.startswith("<!doctype html>")
    # One file: no external stylesheet, script, font or image.
    assert "<link" not in page
    assert 'src="' not in page
    assert "cdn" not in page.lower()


def test_page_matches_a_fresh_build() -> None:
    """Generated, not hand-maintained, so it can never drift from the
    verifier it runs."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        from build_web_verifier import build  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    assert _page() == build()


def test_page_inlines_the_shared_core_rather_than_reimplementing_it() -> None:
    """If the page carried its own copy of the rules it would be a second
    implementation to keep correct (spec 0150 D1)."""
    page = _page()
    core = CORE.read_text(encoding="utf-8")
    for marker in (
        "function leafManifest",
        "function verifyBundle",
        "function chainCitation",
        "function isWithheld",
        "PASS-PARTIAL",
    ):
        assert marker in core
        assert marker in page
    # The inlined copy drops `export` (module scope), and nothing else.
    assert "export function" not in page


# --- the privacy claim, as a test ---------------------------------------------------


def test_the_page_cannot_make_a_network_request() -> None:
    """'Your file never leaves your device' is pinned here rather than
    asserted in prose — a trust tool must not need to be believed."""
    page = _page()
    for api in (
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "navigator.sendBeacon",
        "EventSource",
        "importScripts",
        "import(",
        "<form",
        "<iframe",
        "<img",
        "action=",
    ):
        assert api not in page, f"the page must not be able to use {api}"

    # URLs may appear INSIDE the embedded example bundles — those are real CI
    # log lines, i.e. inert data in a JSON string literal, which cannot cause a
    # request. What must not exist is a URL in markup or code that could be
    # loaded or submitted, so the check is scoped to everything outside the
    # examples block.
    outside = re.sub(r"const EXAMPLES = \{.*?\n\};", "", page, flags=re.S)
    assert "http://" not in outside
    assert "https://" not in outside


def test_the_page_states_what_it_does_not_check() -> None:
    """The same honesty the CLI carries: it can never report a full pass,
    and it says why."""
    page = _page()
    assert "never report a full pass" in page
    assert "PASS-PARTIAL" in page
    assert "Ed25519 signatures are not checked in this build" in page
    assert "never leaves your device" in page


# --- it actually verifies -----------------------------------------------------------


@_needs_node
def test_embedded_examples_verify_in_the_inlined_core() -> None:
    """The embedded honest example passes and the forged one fails — the
    ten-second demo, executed headlessly against the page's own copy."""
    script = r"""
const fs = require('node:fs');
const html = fs.readFileSync('docs/verify.html', 'utf8');
const body = html.match(/<script type="module">([\s\S]*?)<\/script>/)[1];
const upto = body.indexOf('const drop');
const tail = '; return {verifyBundle, parseRaw, EXAMPLES};';
const fn = new Function(body.slice(0, upto) + tail);
const { verifyBundle, parseRaw, EXAMPLES } = fn();
const out = {};
for (const name of ['honest', 'forged']) {
  const report = verifyBundle(parseRaw(EXAMPLES[name]).tree);
  out[name] = {
    verdict: report.verdict,
    integrity: report.integrity_problems.length,
    claims: report.claims.length,
  };
}
console.log(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, cwd=REPO, check=False
    )
    assert proc.returncode == 0, proc.stderr
    result = json.loads(proc.stdout)
    assert result["honest"]["verdict"] == "PASS-PARTIAL"
    assert result["forged"]["verdict"] == "FAIL"
    # The forgery is re-sealed: hashes are perfect in both cases, so only
    # re-execution separates them. That is the whole demo.
    assert result["honest"]["integrity"] == 0
    assert result["forged"]["integrity"] == 0
    assert result["honest"]["claims"] == result["forged"]["claims"] > 0


@_needs_node
def test_the_pages_hash_matches_node_crypto() -> None:
    """The core carries its own SHA-256 so it can run in a browser; it is
    cross-checked against a real implementation so it cannot drift."""
    script = r"""
const { createHash, randomBytes } = require('node:crypto');
const fs = require('node:fs');
const raw = fs.readFileSync('verifier/js/verify-core.mjs', 'utf8');
const src = raw.replace(/\nexport /g, '\n');
const { sha256 } = new Function(src + '; return { sha256 };')();
let bad = 0;
for (let i = 0; i < 300; i += 1) {
  const bytes = randomBytes(i * 3 % 517);
  const mine = sha256(new Uint8Array(bytes));
  const theirs = createHash('sha256').update(bytes).digest('hex');
  if (mine !== theirs) bad += 1;
}
console.log(bad);
"""
    proc = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, cwd=REPO, check=False
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "0"


def test_examples_are_inlined_not_fetched() -> None:
    """Clicking 'try an example' must not become a network request either."""
    page = _page()
    examples = re.search(r"const EXAMPLES = \{(.*?)\n\};", page, re.S)
    assert examples is not None
    assert "tessera-trust-bundle" in examples.group(1)
