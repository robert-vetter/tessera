# 0123. Be findable — MCP registry submissions, staged as artifacts

- **Phase / milestone:** Milestone 19 Unit 2 (ROADMAP2 M19.1). Autonomous
  per CLAUDE.md; everything public-facing here is **staged, not submitted**
  — submissions go out under the maintainer's identity on his say-so (the
  kickoff's hard rule).
- **Issue:** —
- **Status:** approved (autonomous mode).

## Problem

Tessera's MCP server exists and is measured, but nothing points at it. The
discovery substrate for MCP servers is (researched 2026-07-03): the
**official MCP Registry** as upstream — PulseMCP auto-ingests it weekly and
most aggregators (mcp.so, Glama, …) crawl it or GitHub — plus
awesome-mcp-servers as the one high-traffic manual list. Being findable is
therefore one load-bearing submission plus small satellites. This unit
commits everything the maintainer needs to submit in ~45 minutes, with the
facts verified now (schema version, validation mechanics, name collisions)
rather than discovered mid-submission.

**Recorded decisions:**

1. **Everything staged in-repo under `launch/registries/`** — the artifacts
   are part of the deliverable (reviewable, versioned), not a paste bin.
   A `launch/README.md` states the standing rule: nothing in `launch/` is
   published; maintainer identity + timing.
2. **Official registry via PyPI** (its supported route for Python stdio
   servers; schema `2025-12-11`). Verified constraint: the PyPI name
   `tessera` is **taken**; `tessera-trust` is free (both checked
   2026-07-03). The staged `server.json` uses `tessera-trust` and the
   runbook marks the dist-name + version-bump decision as the maintainer's.
   Server name: `io.github.robert-vetter/tessera` (fixed by GitHub-based
   auth regardless of dist name).
3. **The `mcp-name` ownership marker goes into README.md now** as an HTML
   comment — the registry validates PyPI ownership by finding
   `mcp-name: io.github.robert-vetter/tessera` in the package README;
   staging it early is invisible to readers and removes a future step.
4. **Consistency is CI-guarded:** a test pins `server.json` as valid JSON
   with the required shape (name, pypi registryType, stdio transport), its
   two version fields equal, the README marker matching the server name,
   and — once `pyproject.toml`'s version leaves `0.0.0` — the versions in
   sync. Staged artifacts that can drift are drift; these can't.
5. **Blurbs tell the truth:** the simulated actuator (`sent: false`, no
   credential on the server) is stated in every description; no
   "hallucination-free"; the description leads with what the tools do
   (ground / assertions / draft → preview → execute) and the receipt.

## Acceptance criteria

- [ ] `launch/registries/server.json` — schema-`2025-12-11` record, pypi
      package `tessera-trust`, stdio transport, repo + live-demo URLs.
- [ ] `launch/registries/RUNBOOK.md` — the exact submission steps (PyPI →
      mcp-publisher → PulseMCP/mcp.so claims → awesome PR), the two
      decisions called out, the what-not-to-claim rules.
- [ ] `launch/registries/submission-blurb.md` — name/tagline/short/long
      copy for form-based directories.
- [ ] `launch/registries/awesome-mcp-servers-entry.md` — the PR-ready line
      (Knowledge & Memory section, correct emoji legend) + PR title.
- [ ] README.md carries the `mcp-name` comment marker.
- [ ] `tests/test_registry_artifacts.py` — the decision-4 consistency pins.
- [ ] Gate green; eval byte-identical; no engine/eval change.

## Scope

**In:** the four artifacts, the README marker, the consistency test,
`launch/README.md`.
**Out:** any actual submission or account creation; publishing to PyPI;
renaming the distribution (staged as a decision, not performed); changes to
the MCP server itself; Smithery/Glama-specific artifacts (they ingest the
registry/GitHub; revisit only if a pilot partner asks).

## Eval impact

None — docs/metadata + one test. All six lines byte-identical.

## Risks / open questions

- The official registry is in **preview**: schema/reset risk is real and
  recorded in the runbook; the staged file pins the schema version so a
  future mismatch fails loudly at `mcp-publisher publish`, not silently.
- The dist-name decision (`tessera-trust` vs something else) is
  deliberately the maintainer's; the runbook and the version-sync test are
  written so either choice is a two-line change.
- No ADR: nothing here is hard to reverse (a registry record can be
  updated; the README marker is a comment).
