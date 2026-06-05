# 0005. MkDocs Material docs site

- **Phase / milestone:** Phase 0 — Foundation and frame (documentation as a product)
- **Issue:** (none yet)
- **Status:** implemented

## Problem

`docs/ENGINEERING.md` §3 calls a polished docs site the "strahlt nach außen"
piece: it "signals professionalism before anyone reads a line of code." The
project already has substantial Markdown in `docs/`; this unit turns that folder
into a clean, browsable **MkDocs Material** site and wires a **GitHub Actions
docs-deploy** job that builds it and publishes to **GitHub Pages** (Pages source
= GitHub Actions). The reproducible-build discipline applies to docs too: the
site builds from pinned dependencies and the same `uv.lock` world.

## Acceptance criteria

- [ ] `mkdocs.yml` at the repo root: Material theme, a `nav` covering the
      existing `docs/` pages (brief, capabilities, roadmap, SAP alignment,
      engineering, setup, status, ADRs), and a home page.
- [ ] Docs dependencies (`mkdocs-material`) live in a dedicated, **pinned** uv
      dependency group (e.g. `docs`), captured in `uv.lock`.
- [ ] `uv run mkdocs build` succeeds locally; internal links/nav resolve (build
      with strict warnings-as-errors if achievable — see risks).
- [ ] A docs workflow **builds** the site on pull requests (breakage is visible)
      and **deploys** to GitHub Pages on push to `main`, using least-privilege
      `pages: write` + `id-token: write`, the `github-pages` environment, and a
      Pages-appropriate `concurrency` group. Action `uses:` pinned to SHAs.
- [ ] The four `/verify` gates and the existing `gate` CI check are unaffected.
- [ ] README/SETUP note records the one manual step: enable Pages with the
      "GitHub Actions" source (done by the user after this lands).

## Scope

**In:** `mkdocs.yml`, a `docs` dependency group + lockfile update, a home/index
page, and the docs build+deploy workflow with the manual-step note.

**Out:** rewriting or restructuring the existing doc *content*; versioned docs
(`mike`); a custom domain; the README **badges** (unit 8, incl. a docs badge);
**requiring** the docs build as a branch-protection check (that is your repo
setting, not this unit); and the "hello world" app (unit 9).

## Eval impact

None. Documentation tooling; it touches no faithfulness/coverage/quality metric
(the eval harness arrives in Phase 1). It serves Phase 0's "navigable
repository" goal and the project principle that docs are a first-class product.

## Risks / open questions

- **Pages not enabled until after merge.** You enable Pages (Actions source)
  *after* this lands, so the first `main` deploy run may fail until then, then
  succeed on re-run. It is a **separate workflow**, not the required `gate`
  check, so it never blocks PRs. Noted, not blocking.
- **Strict build vs existing links** — **confirmed strict** (warnings-as-errors).
  Some `docs/` pages link to root files (`README.md`, `CLAUDE.md`) outside
  `docs_dir`; the plan will resolve the few such links minimally (a home page
  and/or small link adjustments), without rewriting content.
- **Workflow placement** — **confirmed a dedicated `docs.yml`** with its own
  Pages permissions, keeping `ci.yml` read-only and focused. **No ADR.**
