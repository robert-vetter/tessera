#!/usr/bin/env python3
"""Generate the single-file browser verifier (spec 0150).

Inlines the portable verifier core and two small example bundles into one
self-contained HTML file at ``docs/verify.html``. One file means it works
from ``file://``, from GitHub Pages and from a USB stick — no build step
for the visitor, no CDN, no dependency, and **no network request of any
kind**, which a test pins.

The page is generated rather than hand-maintained so it can never drift
from the verifier it runs: the core is read from
``verifier/js/verify-core.mjs`` and the markup from
``verifier/web/template.html`` at build time, and a test asserts the
committed HTML is byte-identical to a fresh run.

Run: `uv run python scripts/build_web_verifier.py`
"""

from __future__ import annotations

import json
from pathlib import Path

from tessera.bundle.canonical import canonical_bytes
from tessera.bundle.emit import build_bundle, bundle_bytes
from tessera.bundle.mutations import claim_text_edit

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / "verifier" / "js" / "verify-core.mjs"
TEMPLATE = REPO / "verifier" / "web" / "template.html"
OUT = REPO / "docs" / "verify.html"

#: A small real bundle for the embedded examples: the github_actions domain
#: is the project's smallest committed corpus, so the page stays light.
EXAMPLE_DOMAIN = "github_actions"
EXAMPLE_QUESTION = "Why did the Pages deploy fail?"


def examples() -> tuple[str, str]:
    """An honest bundle and its forgery, built deterministically."""
    honest = json.loads(bundle_bytes(build_bundle(EXAMPLE_DOMAIN, EXAMPLE_QUESTION)))
    forged = claim_text_edit(honest).bundle
    return (
        canonical_bytes(honest).decode("utf-8"),
        canonical_bytes(forged).decode("utf-8"),
    )


def build() -> str:
    """The generated page: template + inlined core + inlined examples."""
    # Inside a module script the core's names are already in scope, so the
    # `export` keywords are dropped; nothing else about it changes.
    core = CORE.read_text(encoding="utf-8").replace("\nexport function ", "\nfunction ")
    honest, forged = examples()
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("/*__TESSERA_CORE__*/", core.rstrip())
    page = page.replace('"__TESSERA_HONEST__"', json.dumps(honest))
    page = page.replace('"__TESSERA_FORGED__"', json.dumps(forged))
    return page


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    page = build()
    OUT.write_text(page, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} ({len(page.encode('utf-8')):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
