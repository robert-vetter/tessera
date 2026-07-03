# Registry submissions — the runbook (maintainer-only)

Everything in this directory is **staged, not submitted** (spec 0123;
`launch/README.md`). Facts below verified 2026-07-03. Estimated hands-on
time once the two decisions are made: **~45 minutes**.

## The two decisions this gates on

1. **PyPI distribution name.** The official MCP Registry hosts metadata
   only; the package itself must exist on PyPI. `tessera` is **taken** on
   PyPI, so publishing needs a distribution rename in
   `pyproject.toml [project].name` — staged suggestion: **`tessera-trust`**
   (free as of 2026-07-03). Only the `pip install` name changes: the import
   package (`import tessera`), every CLI entry point (`tessera`,
   `tessera-mcp`, …), and the repo name stay as they are.
2. **First published version.** `pyproject.toml` says `0.0.0`; publishing
   should bump it (suggested `0.1.0`). `server.json`'s two `version` fields
   must match the published version exactly —
   `tests/test_registry_artifacts.py` enforces the sync once the pyproject
   version leaves `0.0.0`.

## Order of operations

The **official MCP Registry is the upstream that matters**: PulseMCP
auto-ingests it (weekly cadence) and most aggregators (mcp.so, Glama, …)
crawl it or GitHub. So: PyPI → official registry → the rest is acceleration
and claiming.

### 1. PyPI (~15 min, one-time)

```bash
# pyproject.toml [project]: name = "tessera-trust", version = "0.1.0"
# launch/registries/server.json: both version fields = "0.1.0"
uv build
uv publish        # needs a pypi.org account + API token
```

The ownership marker is already in the repo README (HTML comment
`mcp-name: io.github.robert-vetter/tessera`); the registry validates PyPI
ownership by finding that string in the package README, and
`readme = "README.md"` ships it. Nothing extra to do.

### 2. Official MCP Registry (~10 min)

```bash
brew install mcp-publisher      # or the GitHub release tarball
cd launch/registries
mcp-publisher login github      # authenticates io.github.robert-vetter/*
mcp-publisher publish           # reads ./server.json, validates ownership
```

Verify: `https://registry.modelcontextprotocol.io/v0/servers?search=tessera`.
The registry is in **preview** (breaking changes / data resets possible);
`server.json` pins schema `2025-12-11`, so a future schema mismatch fails
loudly at publish time rather than silently.

### 3. PulseMCP (~5 min)

Appears automatically within ~a week of step 2 (auto-ingest). To accelerate
or claim: <https://www.pulsemcp.com> → submit/claim, pointing at the GitHub
repo; copy from `submission-blurb.md`.

### 4. mcp.so (~5 min)

<https://mcp.so> → Submit (site form / their GitHub); copy from
`submission-blurb.md`.

### 5. awesome-mcp-servers PR (~10 min)

Fork <https://github.com/punkpeye/awesome-mcp-servers>, add the line from
`awesome-mcp-servers-entry.md` to the **Knowledge & Memory** section in
alphabetical position, open the PR with the title given there.

## What NOT to claim anywhere (CLAUDE.md / MARKET.md rules)

- Never "hallucination-free"; the claim is *provenance + refusal + measured
  faithfulness*.
- The public MCP surface **simulates** execution (`sent: false`, holds no
  credential); real sends are a local, credentialed, approval-gated opt-in.
  Every blurb here says so — keep it when editing.
- LLMs present (optional narration), never attest; the verifier is
  deterministic.
- Don't position as an "MCP gateway" (identity/permission layer, crowded);
  Tessera is the **evidence layer**.
